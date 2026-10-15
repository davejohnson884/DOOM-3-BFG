using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using Encoding = System.Text.Encoding;
using Newtonsoft.Json;
using Reclaimer.Blam.Common;
using Reclaimer.Blam.HaloReach;
using Reclaimer.Geometry;
using TagTool.Animations;
using TagTool.Cache;
using TagTool.Commands.ModelAnimationGraphs;
using TagTool.Tags.Definitions;
using static TagTool.Audio.FMOD;
using Weapon = TagTool.Tags.Definitions.Weapon;
using ReachModel = Reclaimer.Geometry.Model;

internal static class Program
{
    const string ReclaimerRevision = "36224d7a4581f2a1f255099bf706aa56be9f6e21";
    const string TagToolRevision = "ce2dc6ac13072b160752af618ea1dc143e2727ac";
    const string AssemblyRevision = "fd14ef3c46135e9422966c6a64cd926fb0bd23fb";
    static readonly List<string> Errors = [];
    static readonly List<object> Exports = [];
    static readonly JsonSerializerSettings JsonSettings = new() { ReferenceLoopHandling = ReferenceLoopHandling.Ignore };

    [STAThread]
    static int Main(string[] args)
    {
        CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
        try
        {
            NativeLibrary.SetDllImportResolver(typeof(TagTool.Audio.FMOD).Assembly, ResolveNative);
            NativeLibrary.SetDllImportResolver(typeof(Program).Assembly, ResolveNative);
            if (args.Length == 1 && args[0] == "--selftest") return SelfTest();
            bool effectsOnly = args.Length == 5 && args[4] == "--effects";
            if ((!effectsOnly && args.Length != 4) || args[0] != "--mcc" || args[2] != "--out")
                throw new ArgumentException("Usage: ReachAssetExport --mcc <MCC install> --out <output folder> [--effects]");
            var install = Path.GetFullPath(args[1]).TrimEnd(Path.DirectorySeparatorChar);
            var output = Path.GetFullPath(args[3]);
            if (output.Equals(install, StringComparison.OrdinalIgnoreCase) || output.StartsWith(install + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("Output must be outside the MCC install.");
            var map = Path.Combine(install, "haloreach", "maps", "forge_halo.map");
            if (!File.Exists(map)) throw new FileNotFoundException("Reach forge_halo.map was not found.", map);
            var bundle = Path.Combine(output, (effectsOnly ? "reach-effects-" : "reach-assets-") + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(bundle);
            Console.WriteLine("Reading MCC Reach files. Neither game will be launched or modified.");
            var cache = CacheFactory.ReadCacheFile(map);
            if (cache.Metadata.Engine != BlamEngine.HaloReach || !cache.Metadata.IsMcc)
                throw new InvalidDataException("The map is not an MCC Reach cache.");
            var weapon = cache.TagIndex.Where(t => t.ClassCode == "weap" && Normalize(t.TagName).Contains("assault_rifle"))
                .OrderBy(t => t.TagName.Length).FirstOrDefault() ?? throw new InvalidDataException("No assault rifle weapon tag was found.");
            Console.WriteLine($"Assault rifle: {weapon.TagName}; map build: {cache.BuildString}");
            if (effectsOnly) return CollectEffects(cache, weapon, bundle);
            var weaponReferences = new List<IIndexItem>();
            SaveJson(Path.Combine(bundle, "weapon-raw.json"), RawTagCollector.Capture(weapon, Schema("weap.xml"), weaponReferences));
            CaptureCombatReferences(weaponReferences, bundle);
            var fp = RawTagCollector.ReadBlock(cache, weapon.MetaPointer.Address + 0x3B8, 0x20);
            if (fp.Count == 0) throw new InvalidDataException("The assault rifle has no first-person references.");
            var model = Reference(cache, fp.Bytes, 12);
            var graph = Reference(cache, fp.Bytes, 28);
            if (model?.ClassCode != "mode" || graph?.ClassCode != "jmad") throw new InvalidDataException("First-person model/animation references could not be resolved to mode/jmad tags.");
            ExportModel(model, bundle);
            // Keep the actual shared first-person arm rigs as well as the weapon.
            var arms = cache.TagIndex.Where(t => t.ClassCode == "mode" && Normalize(t.TagName).Contains("spartan") &&
                (Normalize(t.TagName).Contains("/fp/") || Normalize(t.TagName).Contains("fp_arms") || Normalize(t.TagName).Contains("first_person"))).Take(8).ToArray();
            foreach (var arm in arms) Attempt("arm model " + arm.TagName, () => ExportModel(arm, bundle));
            var nodes = RawTagCollector.ReadBlock(cache, graph.MetaPointer.Address + 0x48, 0x2C);
            var graphs = CaptureGraphs(graph, bundle);
            Attempt("typed weapon stats", () => ExportWeaponStats(map, weapon.TagName, bundle));
            foreach (var animationGraph in graphs)
                Attempt("decoded animations " + animationGraph.TagName, () => ExportAnimations(map, animationGraph.TagName, bundle));
            Attempt("Reach sounds", () => ExportSounds(install, bundle));
            SaveJson(Path.Combine(bundle, "manifest.json"), new {
                schemaVersion = 1, game = "MCC Reach", map = Path.GetFileName(map), cache.BuildString, cacheType = cache.CacheType.ToString(),
                weapon = weapon.TagName, firstPersonModel = model.TagName, firstPersonGraph = graph.TagName, animationNodeCount = nodes.Count,
                armCandidates = arms.Select(a => a.TagName), reclaimer = ReclaimerRevision, tagTool = TagToolRevision, assembly = AssemblyRevision,
                animationGraphs = graphs.Select(g => g.TagName),
                exports = Exports, errors = Errors,
                status = "Private donor assets and metadata for conversion, not an installed BFG mod. Animation failures are recorded, never replaced with invented motion."
            });
            var zip = bundle + ".zip";
            ZipFile.CreateFromDirectory(bundle, zip, CompressionLevel.Optimal, false);
            Console.WriteLine($"Collected {Exports.Count} asset groups. Recorded issues: {Errors.Count}.");
            PrintUploadFiles(zip);
            return 0;
        }
        catch (Exception ex) { Console.Error.WriteLine("Asset export failed: " + ex); return 1; }
    }

    static string Schema(string name) => Path.Combine(AppContext.BaseDirectory, "schemas", name);
    static IntPtr ResolveNative(string name, System.Reflection.Assembly assembly, DllImportSearchPath? paths) =>
        name == "fmod.dll" ? NativeLibrary.Load(Path.Combine(AppContext.BaseDirectory, "Tools", "fmod.dll")) : IntPtr.Zero;
    static string Normalize(string name) => name.Replace('\\', '/').ToLowerInvariant();
    internal static string SafeName(string name)
    {
        var normalized = name.Replace('\\', '/');
        if (normalized.StartsWith('/') || normalized.Contains(':') || normalized.Split('/').Any(p => p is ".." or ".") || normalized.Any(char.IsControl))
            throw new InvalidDataException("Unsafe asset name.");
        var result = string.Join('_', normalized.Split('/').Select(p => string.Concat(p.Select(c => char.IsLetterOrDigit(c) || c is '_' or '-' ? c : '_'))));
        return result.Length <= 120 ? result : result[..100] + "_" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(name)))[..16];
    }
    static void SaveJson(string path, object value) { Directory.CreateDirectory(Path.GetDirectoryName(path)!); File.WriteAllText(path, JsonConvert.SerializeObject(value, Formatting.Indented, JsonSettings)); }
    static void Attempt(string label, Action action) { try { action(); } catch (Exception ex) { Errors.Add(label + ": " + ex.Message); Console.WriteLine("Recorded issue: " + label + ": " + ex.Message); } }
    static IIndexItem? Reference(ICacheFile cache, byte[] data, int offset)
    {
        var value = BitConverter.ToInt32(data, offset);
        return value == -1 ? null : cache.TagIndex.FirstOrDefault(t => (t.Id & 0xffff) == (value & 0xffff));
    }

    static void ExportModel(IIndexItem tag, string bundle)
    {
        Console.WriteLine("Exporting skinned model: " + tag.TagName);
        if (!ContentFactory.TryGetGeometryContent(tag, out var provider)) throw new InvalidDataException("Reclaimer does not provide this geometry.");
        var scene = provider.GetContent();
        var name = SafeName(tag.TagName);
        var directory = Path.Combine(bundle, "models", name);
        Directory.CreateDirectory(directory);
        scene.WriteRMF(Path.Combine(directory, name + ".rmf"));
        Directory.CreateDirectory(Path.Combine(directory, "textures"));
        foreach (var texture in scene.EnumerateTextures()) Attempt("texture " + texture.Name, () => {
            texture.GetDds().WriteToDisk(Path.Combine(directory, "textures", SafeName(texture.Name) + ".dds"));
        });
        SaveJson(Path.Combine(directory, "model-info.json"), new {
            tag = tag.TagName, scene.CoordinateSystem,
            models = scene.EnumerateModels().Select(m => new { m.Name, m.Bones, meshCount = m.Meshes.Count, materials = m.EnumerateMaterials().Select(mat => new {
                mat.Name, mat.AlphaMode, mappings = mat.TextureMappings.Select(t => new { t.Usage, texture = t.Texture.Name, t.Tiling, channels = t.ChannelMask.ToString() })
            }) })
        });
        Exports.Add(new { kind = "skinned-model", tag = tag.TagName, file = "models/" + name + "/" + name + ".rmf" });
    }

    // Follow actual tag references, including bitmap subimages/arrays. Do not
    // substitute generic art when an effect cannot be decoded.
    static int CollectEffects(ICacheFile cache, IIndexItem weapon, string bundle)
    {
        var roots = new List<IIndexItem> { weapon };
        var frag = cache.TagIndex.Where(t => t.ClassCode == "proj" &&
            Normalize(t.TagName).Contains("frag") && Normalize(t.TagName).Contains("grenade")).ToArray();
        roots.AddRange(frag);
        // Capture the source shader constants for the already exported FP art.
        var armMaterials = new HashSet<string> { "spartan_fp_armor", "spartan_fp_glove",
            "spartan_rubber_suit", "spartan_armor", "spartan_forearm_tricorder" };
        roots.AddRange(cache.TagIndex.Where(t => t.ClassCode == "rmsh" &&
            (Normalize(t.TagName).Contains("/assault_rifle/") ||
             (Normalize(t.TagName).Contains("/spartans/") && armMaterials.Contains(Normalize(t.TagName).Split('/').Last())))));
        if (frag.Length == 0) Errors.Add("No frag projectile found in forge_halo.map; candidate list retained in manifest.");
        var supported = new HashSet<string> { "weap", "proj", "jpt!", "effe", "prt3", "pmdf",
            "hlmt", "mode", "rmsh", "rmtr", "rmfl", "rmcs", "rmw ", "rmfu", "rmfs", "rmmx", "rmhg", "rmss", "rmt2" };
        var pending = new Queue<IIndexItem>(roots);
        var seen = new HashSet<int>();
        var dependencies = new List<object>();
        while (pending.TryDequeue(out var tag))
        {
            if (!seen.Add(tag.Id)) continue;
            if (seen.Count > 256) { Errors.Add("Focused capture reached the 256-tag limit; see dependencies for uncaptured references."); break; }
            if (tag.ClassCode == "bitm") {
                Attempt("effect bitmap " + tag.TagName, () => {
                    if (!ContentFactory.TryGetBitmapContent(tag, out var provider)) throw new InvalidDataException("No bitmap decoder available.");
                    var bitmap = provider.GetContent();
                    if (bitmap.SubmapCount > 64) throw new InvalidDataException("Bitmap exceeds 64 subimages.");
                    for (int i = 0; i < bitmap.SubmapCount; i++) {
                        var file = "effect-bitmaps/" + SafeName(tag.TagName) + "_" + i.ToString("D3") + ".dds";
                        Directory.CreateDirectory(Path.Combine(bundle, "effect-bitmaps"));
                        bitmap.ToDds(i).WriteToDisk(Path.Combine(bundle, file));
                        Exports.Add(new { kind = "effect-bitmap", tag = tag.TagName, submap = i, gamma = bitmap.GetSubmapGamma(i), file });
                    }
                });
                continue;
            }
            if (!supported.Contains(tag.ClassCode)) continue;
            Attempt("effect metadata " + tag.TagName, () => {
                if (tag.ClassCode == "mode") ExportModel(tag, bundle);
                var references = new List<IIndexItem>();
                var schema = Schema(tag.ClassCode.Trim() + ".xml");
                var file = "effect-metadata/" + SafeName(tag.TagName) + "." + tag.ClassCode.Trim() + ".json";
                SaveJson(Path.Combine(bundle, file), RawTagCollector.Capture(tag, schema, references));
                Exports.Add(new { kind = "effect-metadata", tag = tag.TagName, tagClass = tag.ClassCode, file });
                foreach (var target in references) {
                    dependencies.Add(new { source = tag.TagName, sourceClass = tag.ClassCode, target = target.TagName, targetClass = target.ClassCode });
                    // Avoid walking the AR's animation graphs, sounds and unrelated
                    // world models. Frag proj -> hlmt -> mode remains included.
                    if (tag.Id == weapon.Id && target.ClassCode is not ("effe" or "prt3")) continue;
                    if (supported.Contains(target.ClassCode) || target.ClassCode == "bitm") pending.Enqueue(target);
                }
            });
        }
        SaveJson(Path.Combine(bundle, "manifest.json"), new {
            schemaVersion = 2, purpose = "Reach AR flash/casings, frag projectile/art, FP material constants",
            cache.BuildString, reclaimer = ReclaimerRevision, assembly = AssemblyRevision,
            roots = roots.Select(t => new { tag = t.TagName, tagClass = t.ClassCode }),
            fragCandidates = cache.TagIndex.Where(t => Normalize(t.TagName).Contains("frag") && t.ClassCode is "proj" or "mode" or "weap")
                .Select(t => new { tag = t.TagName, tagClass = t.ClassCode }),
            dependencies, exports = Exports, errors = Errors,
            status = "Private source assets for conversion. Does not install or modify either game."
        });
        var zip = bundle + ".zip";
        ZipFile.CreateFromDirectory(bundle, zip, CompressionLevel.Optimal, false);
        Console.WriteLine($"Focused capture complete: {Exports.Count} exports; {Errors.Count} recorded issues.");
        PrintUploadFiles(zip);
        return 0;
    }

    static void CaptureCombatReferences(IEnumerable<IIndexItem> roots, string bundle)
    {
        var pending = new Queue<IIndexItem>(roots.Where(t => t.ClassCode is "proj" or "jpt!"));
        var seen = new HashSet<int>();
        while (pending.TryDequeue(out var tag))
        {
            if (!seen.Add(tag.Id)) continue;
            if (seen.Count > 64) { Errors.Add("Combat reference capture stopped at 64 tags."); break; }
            Attempt("combat metadata " + tag.TagName, () => {
                var references = new List<IIndexItem>();
                SaveJson(Path.Combine(bundle, "combat-metadata", SafeName(tag.TagName) + "." + tag.ClassCode + ".json"),
                    RawTagCollector.Capture(tag, Schema(tag.ClassCode + ".xml"), references));
                foreach (var target in references.Where(t => t.ClassCode is "proj" or "jpt!")) pending.Enqueue(target);
            });
        }
    }

    static List<IIndexItem> CaptureGraphs(IIndexItem root, string bundle)
    {
        var pending = new Queue<IIndexItem>(); pending.Enqueue(root);
        var seen = new HashSet<int>();
        var graphs = new List<IIndexItem>();
        while (pending.TryDequeue(out var tag))
        {
            if (!seen.Add(tag.Id)) continue;
            if (seen.Count > 16) { Errors.Add("Animation inheritance capture stopped at 16 graphs."); break; }
            Attempt("animation graph " + tag.TagName, () => {
                var references = new List<IIndexItem>();
                var directory = Path.Combine(bundle, "animation-graphs", SafeName(tag.TagName));
                SaveJson(Path.Combine(directory, "graph-raw.json"), RawTagCollector.Capture(tag, Schema("jmad.xml"), references));
                graphs.Add(tag);
                foreach (var target in references.Where(t => t.ClassCode == "jmad")) pending.Enqueue(target);
                Attempt("raw resources " + tag.TagName, () => CaptureAnimationResources(tag, directory));
            });
        }
        return graphs;
    }

    static void CaptureAnimationResources(IIndexItem graph, string bundle)
    {
        var cache = graph.CacheFile;
        var groups = RawTagCollector.ReadBlock(cache, graph.MetaPointer.Address + 0x1AC, 12);
        var gestalt = cache.TagIndex.First(t => t.ClassCode == "zone").ReadMetadata<CacheFileResourceGestaltTag>();
        for (int i = 0; i < groups.Count; i++) {
            var resourceId = BitConverter.ToInt32(groups.Bytes, i * 12 + 4);
            var label = "animation resource " + i;
            var member = i;
            Attempt(label, () => {
                var resource = new ResourceIdentifier(resourceId, cache);
                var entry = gestalt.ResourceEntries[resource.ResourceIndex];
                var directory = Path.Combine(bundle, "animation-resources", member.ToString("D3"));
                Directory.CreateDirectory(directory);
                var frames = resource.ReadData(PageType.Auto, 32 * 1024 * 1024);
                if (frames.Length >= 32 * 1024 * 1024) throw new InvalidDataException("Animation resource reaches the capture limit; incomplete bytes will not be exported.");
                File.WriteAllBytes(Path.Combine(directory, "frames.bin"), frames);
                File.WriteAllBytes(Path.Combine(directory, "definition.bin"), RawTagCollector.Bytes(cache, gestalt.FixupDataPointer.Address + entry.FixupOffset, entry.FixupSize));
                SaveJson(Path.Combine(directory, "fixups.json"), new { resourceId, resource.ResourceIndex, entry.FixupSize, resourceFixups = entry.ResourceFixups.ToArray(), definitionFixups = entry.ResourceDefinitionFixups.ToArray() });
                Exports.Add(new { kind = "source-animation-resource", group = member, resourceId });
            });
        }
    }

    static void ExportWeaponStats(string map, string weaponName, string bundle)
    {
        var cache = GameCache.Open(map) ?? throw new InvalidDataException("TagTool does not recognize this map build.");
        using var stream = cache.OpenCacheRead();
        var tag = cache.TagCache.GetTag(weaponName, new TagTool.Common.Tag("weap"));
        SaveJson(Path.Combine(bundle, "weapon-stats.json"), cache.Deserialize<Weapon>(stream, tag));
    }

    static void ExportAnimations(string map, string graphName, string bundle)
    {
        var cache = GameCache.Open(map) ?? throw new InvalidDataException("TagTool does not recognize this map build. Raw graph/resources were retained.");
        var graphTag = cache.TagCache.GetTag(graphName, new TagTool.Common.Tag("jmad"));
        using var stream = cache.OpenCacheRead();
        var graph = cache.Deserialize<ModelAnimationGraph>(stream, graphTag);
        var directory = Path.Combine(bundle, "animations", SafeName(graphName));
        Directory.CreateDirectory(directory);
        var exporter = new ExtractAnimationCommand(cache, graph);
        foreach (var entry in graph.Animations)
        {
            if (entry.AnimationDataBlock == null || entry.AnimationDataBlock.Count == 0) continue;
            entry.AnimationData = entry.AnimationDataBlock[0];
            var type = entry.AnimationData.AnimationTypeReach;
            entry.AnimationData.AnimationType = type == ModelAnimationGraph.FrameTypeReach.None ? ModelAnimationGraph.FrameType.Base : (ModelAnimationGraph.FrameType)(type - 1);
        }
        // Resolve bind poses once per graph, rather than rescanning every render model for every clip.
        var defaults = AnimationDefaultNodeHelper.GetNodeDefaultValues(cache, graph);
        SaveJson(Path.Combine(directory, "default-nodes.json"), defaults);
        if (defaults.Any(n => !float.IsFinite(n.Scale) || n.Scale <= 0 || !float.IsFinite(n.Rotation.LengthSquared()) || n.Rotation.LengthSquared() < 0.5f))
            throw new InvalidDataException("The animation graph has missing/invalid default model nodes; raw data was retained.");
        var records = new List<object>();
        for (int i = 0; i < graph.Animations.Count; i++) {
            var index = i;
            var name = cache.StringTable.GetString(graph.Animations[i].Name);
            // The upstream exporter makes a filename from this name.
            if (string.IsNullOrWhiteSpace(name) || name.Replace(':', ' ').IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || name.Contains("..")) {
                Errors.Add("Unsafe animation name skipped: index " + index); continue;
            }
            Attempt("animation " + name, () => {
                var entry = graph.Animations[index];
                if (entry.AnimationData == null) throw new InvalidDataException("Inherited clip; see captured shared/parent graph.");
                var data = exporter.BuildAnimationResourceData(entry) ?? throw new InvalidDataException("Unsupported animation resource.");
                var animation = new TagTool.Animations.Animation(defaults, data);
                var type = entry.AnimationData.AnimationType;
                var world = entry.AnimationData.InternalFlags.HasFlag(ModelAnimationGraph.Animation.InternalFlagsValue.WorldRelative);
                var extension = animation.GetAnimationExtension((int)type, (int)entry.AnimationData.FrameInfoType, world);
                // Use the upstream overlay/replacement composition, with per-clip failure isolation.
                if (type is ModelAnimationGraph.FrameType.Overlay or ModelAnimationGraph.FrameType.Replacement)
                {
                    var baseEntry = exporter.GetBaseAnimation(name);
                    if (baseEntry != null)
                    {
                        var baseData = exporter.BuildAnimationResourceData(baseEntry) ?? throw new InvalidDataException("The required base animation could not be decoded.");
                        var baseAnimation = new TagTool.Animations.Animation(defaults, baseData);
                        if (type == ModelAnimationGraph.FrameType.Overlay) { animation.Overlay(baseAnimation); animation.InsertBaseFrame(baseAnimation); }
                        else animation.Replace(baseAnimation);
                    }
                    else if (type == ModelAnimationGraph.FrameType.Overlay) { animation.Overlay(); animation.InsertBaseFrame(); }
                    else throw new InvalidDataException("Replacement clip has no decoded base animation.");
                }
                var file = index.ToString("D4") + "_" + SafeName(name.Replace(':', ' ')) + "." + extension;
                Console.WriteLine("Exporting animation: " + name);
                animation.Export(Path.Combine(directory, file));
                records.Add(new { name, index, source = entry, files = new[] { file } });
            });
        }
        SaveJson(Path.Combine(directory, "animation-events.json"), records);
        Exports.Add(new { kind = "decoded-animation-clips", count = records.Count, tag = graphName });
    }

    static void Check(FMOD_RESULT result) { if (result != FMOD_RESULT.OK) throw new InvalidDataException("FMOD: " + result); }
    [DllImport("fmod.dll", EntryPoint = "FMOD_System_SetOutput")]
    static extern FMOD_RESULT SetFmodOutput(IntPtr system, int output);
    static void InitDecoder(FMODSystem system)
    {
        // FMOD_OUTPUTTYPE_NOSOUND = 2: decode without requiring an audio device.
        Check(SetFmodOutput(system.Handle, 2));
        Check(system.Init(32, FMOD_INITFLAGS.NORMAL));
    }
    static void ExportSounds(string install, string bundle)
    {
        var bankPath = Path.Combine(install, "haloreach", "fmod", "pc", "sfx.fsb");
        using var info = new BinaryReader(File.OpenRead(bankPath + ".info"));
        if (info.BaseStream.Length % 280 != 0) throw new InvalidDataException("Unexpected FMOD info record size.");
        var selected = new List<(int Index, string Name)>();
        for (int index = 0; info.BaseStream.Position < info.BaseStream.Length; index++) {
            var record = info.ReadBytes(280);
            var name = Encoding.UTF8.GetString(record, 24, 256).Split('\0')[0];
            var lower = Normalize(name);
            if (lower.Contains("assault_rifle") || lower.Contains("frag_grenade")) selected.Add((index, name));
        }
        if (selected.Count == 0) throw new InvalidDataException("No assault-rifle/frag sound paths were found.");
        SaveJson(Path.Combine(bundle, "sound-index.json"), new { selectedCount = selected.Count, limit = 128,
            samples = selected.Select(s => new { s.Index, s.Name }) });
        if (selected.Count > 128) Errors.Add("Sound export capped at 128 samples; full selected index retained.");
        Check(FMODSystem.Create(out var system));
        using (system) {
            InitDecoder(system);
            Check(system.CreateStream(bankPath, FMOD_MODE.OPENONLY | FMOD_MODE.ACCURATETIME, out var bank));
            using (bank) foreach (var item in selected.Take(128)) Attempt("sound " + item.Name, () => {
                Check(bank.GetSubSound(item.Index, out var sound));
                using (sound) {
                    Check(sound.GetLength(out var length, FMOD_TIMEUNIT.PCMBYTES));
                    if (length > 32 * 1024 * 1024) throw new InvalidDataException("Sound sample exceeds the size limit.");
                    Check(sound.GetFormat(out _, out var format, out var channels, out var bits));
                    Check(sound.GetDefaults(out var frequency, out _));
                    Check(sound.SeekData(0));
                    var pcm = new byte[length];
                    var result = sound.ReadData(pcm, length, out var read);
                    if (result != FMOD_RESULT.OK && result != FMOD_RESULT.ERR_FILE_EOF) Check(result);
                    if (read != length) throw new InvalidDataException("Incomplete decoded PCM sample.");
                    var name = item.Index.ToString("D5") + "_" + SafeName(item.Name) + ".wav";
                    var directory = Path.Combine(bundle, "sounds");
                    Directory.CreateDirectory(directory);
                    WriteWave(Path.Combine(directory, name), pcm, (int)Math.Round(frequency), channels, bits, format == FMOD_SOUND_FORMAT.PCMFLOAT);
                    Exports.Add(new { kind = "sound", item.Index, source = item.Name, file = "sounds/" + name, sampleRate = frequency, channels, bits });
                }
            });
        }
    }

    internal static void WriteWave(string file, byte[] pcm, int rate, int channels, int bits, bool floating)
    {
        if (rate < 8000 || rate > 192000 || channels < 1 || channels > 8 || bits is not (8 or 16 or 24 or 32) || pcm.Length % (channels * bits / 8) != 0)
            throw new InvalidDataException("Invalid PCM format.");
        using var writer = new BinaryWriter(File.Create(file));
        writer.Write(Encoding.ASCII.GetBytes("RIFF")); writer.Write(36 + pcm.Length + (pcm.Length & 1));
        writer.Write(Encoding.ASCII.GetBytes("WAVEfmt ")); writer.Write(16); writer.Write((short)(floating ? 3 : 1));
        writer.Write((short)channels); writer.Write(rate); writer.Write(rate * channels * bits / 8);
        writer.Write((short)(channels * bits / 8)); writer.Write((short)bits);
        writer.Write(Encoding.ASCII.GetBytes("data")); writer.Write(pcm.Length); writer.Write(pcm);
        if ((pcm.Length & 1) != 0) writer.Write((byte)0);
    }

    static void PrintUploadFiles(string zip)
    {
        const int partSize = 24 * 1024 * 1024;
        using var hashStream = File.OpenRead(zip);
        var hash = Convert.ToHexString(SHA256.HashData(hashStream));
        Console.WriteLine("Private asset ZIP SHA256: " + hash);
        if (new FileInfo(zip).Length <= partSize) { Console.WriteLine("Attach this private asset ZIP: " + zip); return; }
        using var input = File.OpenRead(zip);
        var buffer = new byte[partSize];
        for (int part = 1; input.Position < input.Length; part++) {
            var length = input.ReadAtLeast(buffer, (int)Math.Min(partSize, input.Length - input.Position));
            var file = zip + ".part" + part.ToString("D3");
            File.WriteAllBytes(file, buffer.AsSpan(0, length).ToArray());
            Console.WriteLine("Attach this numbered ZIP part: " + file);
        }
    }

    static int SelfTest()
    {
        var root = Path.Combine(Path.GetTempPath(), "reach-asset-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try {
            foreach (var schema in new[] { "weap", "proj", "jpt!", "effe", "prt3", "pmdf", "hlmt", "mode", "rmsh" }) {
                var xml = System.Xml.Linq.XDocument.Load(Schema(schema + ".xml"));
                if (xml.Root?.Attribute("baseSize") == null) throw new Exception("Missing effect schema: " + schema);
            }
            foreach (var bad in new[] { "../escape", "C:/escape", "/escape", "ok/../../escape" }) {
                bool rejected = false; try { SafeName(bad); } catch (InvalidDataException) { rejected = true; }
                if (!rejected) throw new Exception("Unsafe path was accepted.");
            }
            if (SafeName("objects\\weapons\\assault_rifle") != "objects_weapons_assault_rifle") throw new Exception("Name normalization failed.");
            var wave = Path.Combine(root, "sample.wav"); WriteWave(wave, new byte[16], 48000, 2, 16, false);
            var bytes = File.ReadAllBytes(wave);
            if (Encoding.ASCII.GetString(bytes, 0, 4) != "RIFF" || BitConverter.ToInt32(bytes, 4) != bytes.Length - 8 || BitConverter.ToInt32(bytes, 40) != 16)
                throw new Exception("PCM WAVE header is invalid.");
            var model = new ReachModel { Name = "synthetic_rig" };
            model.Bones.Add(new Bone { Name = "root", ParentIndex = -1 });
            var scene = Scene.WrapSingleModel(model, 3048);
            var rmf = Path.Combine(root, "rig.rmf"); scene.WriteRMF(rmf);
            if (new FileInfo(rmf).Length < 64) throw new Exception("No RMF skeleton was written.");
            Check(FMODSystem.Create(out var system));
            using (system) {
                InitDecoder(system);
                Check(system.CreateStream(wave, FMOD_MODE.OPENONLY | FMOD_MODE.ACCURATETIME, out var sound));
                using (sound) {
                    Check(sound.GetLength(out var length, FMOD_TIMEUNIT.PCMBYTES));
                    Check(sound.GetFormat(out _, out _, out var channels, out var bits));
                    var pcm = new byte[length];
                    var result = sound.ReadData(pcm, length, out var read);
                    if (result != FMOD_RESULT.OK && result != FMOD_RESULT.ERR_FILE_EOF) Check(result);
                    if (length != 16 || read != 16 || channels != 2 || bits != 16) throw new Exception("Native PCM decoding failed.");
                }
            }
            var oddWave = Path.Combine(root, "odd.wav"); WriteWave(oddWave, new byte[3], 8000, 1, 8, false);
            var odd = File.ReadAllBytes(oddWave);
            if (odd.Length != 48 || BitConverter.ToInt32(odd, 4) != 40 || BitConverter.ToInt32(odd, 40) != 3) throw new Exception("Odd PCM padding failed.");
            Console.WriteLine("PASS: Reclaimer rig serialization, native PCM decoding, WAVE headers and asset path guards. No game assets were read.");
            return 0;
        } finally { Directory.Delete(root, true); }
    }
}
