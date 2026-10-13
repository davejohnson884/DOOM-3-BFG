using System.Xml.Linq;
using Reclaimer.Blam.Common;
using Reclaimer.Blam.MccHaloReach;

internal static class RawTagCollector
{
    internal record Block(long Address, int Count, int ElementSize, byte[] Bytes);

    internal static long Address(ICacheFile cache, int packed)
    {
        if (cache is not CacheFile reach) throw new InvalidDataException("Expected an MCC Reach cache.");
        return cache.DefaultAddressTranslator.GetAddress(reach.PointerExpander.Expand(packed));
    }

    internal static byte[] Bytes(ICacheFile cache, long address, int length)
    {
        using var reader = cache.CreateReader(cache.DefaultAddressTranslator);
        if (length < 0 || length > 32 * 1024 * 1024 || address < 0 || address > reader.BaseStream.Length - length)
            throw new InvalidDataException("Tag data range is outside the map or exceeds the read limit.");
        reader.Seek(address, SeekOrigin.Begin);
        var data = reader.ReadBytes(length);
        if (data.Length != length) throw new EndOfStreamException();
        return data;
    }

    internal static Block ReadBlock(ICacheFile cache, long header, int size)
    {
        var raw = Bytes(cache, header, 12);
        var count = BitConverter.ToInt32(raw, 0);
        var pointer = BitConverter.ToInt32(raw, 4);
        if (count < 0 || count > 100000) throw new InvalidDataException("Invalid tag block count.");
        if (count == 0) return new Block(0, 0, size, []);
        if (size < 1) throw new InvalidDataException("Invalid nonempty tag block size.");
        var address = Address(cache, pointer);
        return new Block(address, count, size, Bytes(cache, address, checked(count * size)));
    }

    internal static object Capture(IIndexItem tag, string schema, ICollection<IIndexItem>? references = null)
    {
        var root = XDocument.Load(schema).Root ?? throw new InvalidDataException("Missing tag schema.");
        int remaining = 16 * 1024 * 1024;
        return CaptureNode(tag.CacheFile, tag.MetaPointer.Address, Number(root, "baseSize"), root, 0, ref remaining, references);
    }

    static object CaptureNode(ICacheFile cache, long address, int size, XElement schema, int depth, ref int remaining, ICollection<IIndexItem>? references)
    {
        if (depth > 16 || size > remaining) throw new InvalidDataException("Metadata graph exceeds capture limits.");
        remaining -= size;
        var raw = Bytes(cache, address, size);
        var fields = new List<object>();
        foreach (var field in schema.Elements())
        {
            var kind = field.Name.LocalName.ToLowerInvariant();
            if (kind is not ("tagref" or "stringid")) continue;
            var offset = Number(field, "offset");
            var required = kind == "tagref" ? 16 : 4;
            if (offset < 0 || offset > raw.Length - required) throw new InvalidDataException("Schema field exceeds its record.");
            var id = BitConverter.ToInt32(raw, offset + (kind == "tagref" ? 12 : 0));
            if (kind == "stringid")
            {
                cache.StringIndex.TryGetValue(id, out var text);
                fields.Add(new { kind, name = (string?)field.Attribute("name"), offset, id, text });
            }
            else
            {
                var target = id == -1 ? null : cache.TagIndex.FirstOrDefault(t => (t.Id & 0xffff) == (id & 0xffff));
                if (target != null) references?.Add(target);
                fields.Add(new { kind, name = (string?)field.Attribute("name"), offset, id, tag = target?.TagName, tagClass = target?.ClassCode });
            }
        }
        var children = new Dictionary<string, object>();
        foreach (var field in schema.Elements("tagblock"))
        {
            var block = ReadBlock(cache, address + Number(field, "offset"), Number(field, "elementSize"));
            if (block.Bytes.Length > remaining) throw new InvalidDataException("Metadata graph exceeds capture limits.");
            var elements = new List<object>();
            for (int i = 0; i < block.Count; i++)
                elements.Add(CaptureNode(cache, block.Address + i * block.ElementSize, block.ElementSize, field, depth + 1, ref remaining, references));
            children[(string?)field.Attribute("name") ?? "unnamed"] = new { block.Address, block.Count, block.ElementSize, elements };
        }
        return new { address, size, raw, fields, children };
    }

    static int Number(XElement element, string name)
    {
        var text = (string?)element.Attribute(name) ?? throw new InvalidDataException($"Missing schema {name}.");
        return text.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? Convert.ToInt32(text[2..], 16) : int.Parse(text);
    }
}
