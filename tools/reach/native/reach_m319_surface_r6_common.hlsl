// rpUser0: normalized age, columns, rows, frame count (one for static art).
// rpUser1: linear RGB gain, independent alpha gain.
// rpUser2: world depth-fade distance, inner tile scale, tile inset, shell rim power.
// rpUser3: near-camera fade distance, shell rim floor, reserved, reserved.
#include "global_inc.hlsl"
#ifndef REACH_MSAA_DEPTH
#define REACH_MSAA_DEPTH 0
#endif
Texture2D<float4> t_Atlas : register(t0 VK_DESCRIPTOR_SET(0));
#if REACH_MSAA_DEPTH
Texture2DMS<float> t_SceneDepth : register(t2 VK_DESCRIPTOR_SET(0));
#else
Texture2D<float> t_SceneDepth : register(t2 VK_DESCRIPTOR_SET(0));
#endif
SamplerState s_Atlas : register(s0 VK_DESCRIPTOR_SET(1));
struct PS_IN {
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float3 toEye : TEXCOORD2;
    float4 color : COLOR0;
};
struct PS_OUT { float4 color : SV_Target0; };
float eyeDepth(float d) {
    float denominator=d*rpProjectionMatrixW.z-rpProjectionMatrixZ.z;
    return abs(rpProjectionMatrixZ.w)/max(abs(denominator),0.0000001);
}
float4 atlasFrame(float frame, float2 uv) {
    float2 cell=float2(fmod(frame,rpUser0.y),floor(frame/rpUser0.y));
    float2 inCell=saturate(uv)*rpUser2.y+rpUser2.z;
    float2 scale=1.0/rpUser0.yz;
    // Gradients exclude frame changes, and the gutter protects adjacent cells.
    float2 dx=ddx(uv)*rpUser2.y*scale;
    float2 dy=ddy(uv)*rpUser2.y*scale;
    return t_Atlas.SampleGrad(s_Atlas,(cell+inCell)*scale,dx,dy);
}
void main(PS_IN f, out PS_OUT o) {
    float frame=saturate(rpUser0.x)*max(rpUser0.w-1.0,0.0);
    float a=floor(frame), b=min(a+1.0,rpUser0.w-1.0);
    float4 color=lerp(atlasFrame(a,f.uv),atlasFrame(b,f.uv),frac(frame));
    float fade=1.0;
    if(rpUser2.x>0.0) {
        uint width,height;
        float sceneZ;
        int2 pixel=int2(f.position.xy);
#if REACH_MSAA_DEPTH
        uint samples;
        t_SceneDepth.GetDimensions(width,height,samples);
        pixel=clamp(pixel,int2(0,0),int2(width-1,height-1));
        sceneZ=1e20;
        for(uint sample=0;sample<samples;++sample) sceneZ=min(sceneZ,eyeDepth(t_SceneDepth.Load(pixel,sample)));
#else
        t_SceneDepth.GetDimensions(width,height);
        pixel=clamp(pixel,int2(0,0),int2(width-1,height-1));
        sceneZ=eyeDepth(t_SceneDepth.Load(int3(pixel,0)));
#endif
        float gap=max(sceneZ-eyeDepth(f.position.z),0.0);
        fade=smoothstep(0.0,rpUser2.x,gap);
    }
    if(rpUser3.x>0.0) fade*=smoothstep(0.0,rpUser3.x,length(f.toEye));
    if(rpUser2.w>0.0) {
        float rim=pow(saturate(1.0-abs(dot(normalize(f.normal),normalize(f.toEye)))),rpUser2.w);
        fade*=lerp(rpUser3.y,1.0,rim);
    }
    // RGB is already premultiplied by coverage in the bake; interpolate it once.
    // Native vertex RGB already carries its particle fade: do not multiply it
    // by vertex alpha a second time.
    o.color=float4(color.rgb*rpUser1.rgb*f.color.rgb,color.a*rpUser1.a*f.color.a)*fade;
}
