def extend(changed, replace):
    path='neo/renderer/ModelManager.cpp'
    changed[path]=replace(changed[path], '#include "Model_local.h"\n', '#include "Model_local.h"\n#include "ReachSpartanModelAliases.h"\n', path)
    changed[path]=replace(changed[path], '\tcanonical.ToLower();\n', '''\tcanonical.ToLower();
    // Reach opt-in weapon projection / compatible saved Spartan player models.
    // Saved render entities retain mesh paths independently of modelDefs.
    // Resolve before cache lookup, only in Reach and only when the new mesh exists.
    if( idStr::Icmp(cvarSystem->GetCVarString("fs_game"), "reach") == 0 )
    {
        canonical.BackSlashesToSlashes();
        const char* replacement=ReachSpartan::Replacement(canonical.c_str());
        if( replacement != NULL && fileSystem->ReadFile(replacement, NULL, NULL) >= 0 )
        {
            canonical=replacement;
        }
    }
''',path)
    return changed
