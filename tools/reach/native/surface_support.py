"""Opt-in M319 material quality: BC7, linear mipmaps and soft scene intersections."""
from pathlib import Path

EXTRA_PATHS=['neo/renderer/Image_load.cpp','neo/renderer/BinaryImage.cpp','neo/renderer/NVRHI/Image_NVRHI.cpp','neo/renderer/Image_intrinsic.cpp','neo/shaders/shaders.cfg','neo/renderer/Model_prt.cpp']
SHADERS=['reach_m319_surface_r6.vs.hlsl','reach_m319_surface_r6.ps.hlsl','reach_m319_surface_r6_msaa.ps.hlsl','reach_m319_surface_r6_common.hlsl']

def extend(changed,replace):
    f=EXTRA_PATHS[0];s=changed[f]
    anchor='\t\t\tcase TD_DEFAULT:\n\t\t\t\topts.gammaMips = true;\n\t\t\t\topts.format = FMT_DXT5;\n\t\t\t\topts.colorFormat = CFM_DEFAULT;\n'
    s=replace(s,anchor,anchor+'''                // Reach opt-in weapon projection / linear premultiplied FX atlas.
                if(!idStr::Icmpn(imgName.c_str(),"textures/reach/m319/fx/r6/",sizeof("textures/reach/m319/fx/r6/")-1)) {
                    opts.gammaMips=false;
                    opts.format=FMT_BC7;
                }
''',f);changed[f]=s
    f=EXTRA_PATHS[1];s=changed[f]
    s=replace(s,'#pragma hdrstop\n','#pragma hdrstop\n// Reach opt-in weapon projection / existing ISPC BC7 encoder.\n#include "../libs/ispc_texcomp/ispc_texcomp.h"\n',f)
    anchor='\n\t\telse if( textureFormat == FMT_BC6H )\n'
    assert s.count(anchor)==2,f
    s=s.replace(anchor,'''
        else if(textureFormat==FMT_BC7) {
            img.Alloc(dxtWidth*dxtHeight);
            rgba_surface surface={dxtPic,dxtWidth,dxtHeight,dxtWidth*4};
            bc7_enc_settings settings;
            GetProfile_alpha_slow(&settings);
            CompressBlocksBC7(&surface,img.data,&settings);
        }
'''+anchor);changed[f]=s
    f=EXTRA_PATHS[2];s=changed[f]
    anchor='\t\tcase FMT_BC6H:\n'
    s=replace(s,anchor,'''        // Reach opt-in weapon projection / BC7 preserves soft RGBA gradients.
        case FMT_BC7:
            format=nvrhi::Format::BC7_UNORM;
            break;
'''+anchor,f);changed[f]=s
    f=EXTRA_PATHS[3];s=changed[f]
    anchor='\tcurrentDepthImage = ImageFromFunction( "_currentDepth", R_DepthImage );\n'
    s=replace(s,anchor,anchor+'''    // Reach opt-in weapon projection / isolated read-only particle depth copy.
    ImageFromFunction("_reachM319SceneDepth",R_DepthImage);
''',f);changed[f]=s
    f=EXTRA_PATHS[4];s=changed[f];s+='\n// Reach opt-in weapon projection / source-based M319 surface programs.\n'
    for name in SHADERS[:3]:
        s+=name+' -T '+('vs' if '.vs.' in name else 'ps')+' -D USE_GPU_SKINNING=0\n'
    changed[f]=s
    f='neo/renderer/RenderBackend.cpp';s=changed[f]
    anchor='\tfloat currentGuiStereoOffset = 0.0f;\n'
    s=replace(s,anchor,anchor+'    bool reachM319DepthCopied=false; // Reach opt-in weapon projection / per-view soft depth.\n',f)
    anchor='\t\t\t\trenderProgManager.BindProgram( newStage->glslProgram );\n'
    s=replace(s,anchor,'''                int surfaceProgram=newStage->glslProgram;
                if(!surf->space->isGuiSurface && !idStr::Icmpn(shader->GetName(),"reach/m319/r6/",14)) {
                    if(!reachM319DepthCopied) {
                        idImage* depth=globalImages->ImageFromFile("_reachM319SceneDepth",TF_NEAREST,TR_CLAMP,TD_DEPTH_STENCIL);
                        const nvrhi::TextureDesc& source=globalImages->currentDepthImage->GetTextureHandle()->getDesc();
                        if(!depth->GetTextureHandle() || depth->GetUploadWidth()!=int(source.width) ||
                           depth->GetUploadHeight()!=int(source.height) || depth->GetTextureHandle()->getDesc().sampleCount!=source.sampleCount) {
                            depth->GenerateImage(NULL,source.width,source.height,TF_NEAREST,TR_CLAMP,TD_DEPTH_STENCIL,commandList,true,false,source.sampleCount);
                        }
                        commandList->copyTexture(depth->GetTextureHandle(),nvrhi::TextureSlice(),globalImages->currentDepthImage->GetTextureHandle(),nvrhi::TextureSlice());
                        reachM319DepthCopied=true;
                    }
                    if(R_GetMSAASamples()>1) {
                        idList<shaderMacro_t> macros={ {"USE_GPU_SKINNING","0"} };
                        const int pixel=renderProgManager.FindShader("reach_m319_surface_r6_msaa",SHADER_STAGE_FRAGMENT,"",macros,false,LAYOUT_DRAW_VERT);
                        surfaceProgram=renderProgManager.FindProgram("reach_m319_surface_r6_msaa",newStage->vertexProgram,pixel,BINDING_LAYOUT_POST_PROCESS_INGAME);
                    }
                }
                renderProgManager.BindProgram(surfaceProgram);
''',f);changed[f]=s
    f='neo/renderer/Model_prt.cpp';s=changed[f]
    anchor='\t\tidRandom steppingRandom, steppingRandom2;\n'
    s=replace(s,anchor,anchor+'''        // Reach opt-in weapon projection / decorrelate fixed-range visual groups.
        // The stock model gives every stage the same seed, aligning independent
        // bursts into repeated beads. Salt only this material namespace. No
        // game RNG, count, clock, velocity law, archive or entity state changes.
        const int reachVisualSalt=!idStr::Icmpn(stage->material->GetName(),"reach/m319/r6/",14) ?
            (((stageNum+1)*7919)&idRandom::MAX_RAND) : 0;
''',f)
    anchor='^ ( int )( renderEntity->shaderParms[SHADERPARM_DIVERSITY] * idRandom::MAX_RAND ) );'
    assert s.count(anchor)==2,f
    s=s.replace(anchor,'^ ( int )( renderEntity->shaderParms[SHADERPARM_DIVERSITY] * idRandom::MAX_RAND ) ^ reachVisualSalt );')
    changed[f]=s
    return changed

def install(root,source):
    for name in SHADERS:
        (Path(root)/'neo/shaders'/name).write_bytes((Path(source)/name).read_bytes())
