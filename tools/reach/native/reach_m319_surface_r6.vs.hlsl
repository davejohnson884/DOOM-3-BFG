// Source-based M319 materials: linear HDR, premultiplied flipbooks and soft depth.
#include "global_inc.hlsl"
struct VS_IN {
    float4 position : POSITION;
    float2 texcoord : TEXCOORD0;
    float4 normal : NORMAL;
    float4 tangent : TANGENT;
    float4 color : COLOR0;
    float4 color2 : COLOR1;
};
struct VS_OUT {
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float3 toEye : TEXCOORD2;
    float4 color : COLOR0;
};
void main(VS_IN v, out VS_OUT o) {
    o.position=float4(dot4(v.position,rpMVPmatrixX),dot4(v.position,rpMVPmatrixY),dot4(v.position,rpMVPmatrixZ),dot4(v.position,rpMVPmatrixW));
    o.uv=v.texcoord;
    o.normal=v.normal.xyz*2.0-1.0;
    o.toEye=rpLocalViewOrigin.xyz-v.position.xyz;
    o.color=swizzleColor(v.color);
}
