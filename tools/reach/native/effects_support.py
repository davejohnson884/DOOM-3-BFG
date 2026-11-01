"""Opt-in damped particle motion and M319 mesh/particle FX composition."""
def extend(changed,replace):
 f='neo/framework/DeclParticle.h';s=changed[f];s=replace(s,'\tPPATH_DRIP\n','\tPPATH_DRIP,\n\tPPATH_REACH_DAMPED // Reach opt-in weapon projection / visual-only drag\n',f);changed[f]=s
 f='neo/framework/DeclParticle.cpp';s=changed[f];s=replace(s,'#pragma hdrstop\n','#pragma hdrstop\n#include "ReachEffectMotion.h" // Reach opt-in weapon projection / visual-only paths\n',f)
 s=replace(s,'\t{ "drip", 2, "something something" }','\t{ "drip", 2, "something something" },\n\t{ "reachDamped", 2, "linear drag, world Z acceleration" }',f)
 s=replace(s,'if( customPathType == PPATH_STANDARD )','if( customPathType == PPATH_STANDARD || customPathType == PPATH_REACH_DAMPED )',f)
 s=replace(s,'\t\tfloat iSpeed = speed.Integrate( g->frac, g->random );\n\t\torigin += dir * iSpeed * particleLife;','''        if(customPathType == PPATH_REACH_DAMPED) {
            origin += dir * speed.Eval(0.0f,g->random) * ReachEffectMotion::Travel(g->age,customPathParms[0]);
        } else {
            float iSpeed = speed.Integrate( g->frac, g->random );
            origin += dir * iSpeed * particleLife;
        }''',f)
 s=replace(s,'\t// add gravity after adjusting for axis\n','''    if(customPathType == PPATH_REACH_DAMPED) {
        idVec3 acceleration(0,0,customPathParms[1]);
        acceleration *= g->renderEnt->axis.Transpose();
        origin += acceleration * ReachEffectMotion::AccelerationTravel(g->age,customPathParms[0]);
    }
\t// add gravity after adjusting for axis
''',f);changed[f]=s
 f='neo/renderer/RenderBackend.cpp';s=changed[f]
 s=replace(s,'\t\t\trenderLog.OpenBlock( "Standard Shader Stage", colorGreen );\n\t\t\tGL_Color( color );','''            // Reach opt-in weapon projection / linear HDR for source-based FX.
            // GL_Color and the ordinary 3D shader both clamp to one. The
            // existing pass-through variant preserves RGB intensity and linear
            // coverage, exclusively for these unskinned explicit-UV materials.
            const bool reachLinearFX = !surf->space->isGuiSurface && !surf->jointCache &&
                pStage->texture.texgen == TG_EXPLICIT && !pStage->texture.cinematic &&
                !idStr::Icmpn(shader->GetName(),"reach/m319/r5/",14);
            renderLog.OpenBlock( "Standard Shader Stage", colorGreen );
            if(reachLinearFX) {
                color[0]=Max(0.0f,color[0]);color[1]=Max(0.0f,color[1]);color[2]=Max(0.0f,color[2]);
                color[3]=idMath::ClampFloat(0.0f,1.0f,color[3]);
                SetFragmentParm(RENDERPARM_COLOR,color.ToFloatPtr());
            } else {
                GL_Color(color);
            }''',f)
 anchor='\t\t\t\telse\n\t\t\t\t{\n\t\t\t\t\trenderProgManager.BindShader_TextureVertexColor();\n\t\t\t\t}\n\t\t\t}\n\n\t\t\tRB_SetVertexColorParms( svc );'
 s=replace(s,anchor,'''                else
                {
                    if(reachLinearFX) renderProgManager.BindShader_TextureVertexColor_sRGB();
                    else renderProgManager.BindShader_TextureVertexColor();
                }
            }

            RB_SetVertexColorParms( svc );''',f);changed[f]=s
 f='neo/d3xp/Projectile.cpp';s=changed[f]
 s=replace(s,'#include "ReachM319Policy.h"','#include "ReachM319Policy.h"\n#include "Fx.h"',f)
 s=replace(s,'\t// change the model, usually to a PRT\n','''    // Reach opt-in weapon projection / compose the source mesh with particles.
    // A decl opt-in keeps every other projectile and old asset pack unchanged.
    if(!common->IsMultiplayer() && spawnArgs.GetBool("reach_m319")) {
        const char* visualFx=spawnArgs.GetString("fx_reach_detonate");
        if(visualFx[0]) {
            idEntityFx::StartFx(visualFx,&GetPhysics()->GetOrigin(),&mat3_identity,NULL,false);
            spawnArgs.SetInt("_m319_visualStart",gameLocal.time);
            if(cvarSystem->GetCVarBool("g_debugWeapon"))
                gameLocal.Printf("[M319FX] START time=%d effect=%s\\n",gameLocal.time,visualFx);
        }
    }
\t// change the model, usually to a PRT
''',f);changed[f]=s
 return changed
