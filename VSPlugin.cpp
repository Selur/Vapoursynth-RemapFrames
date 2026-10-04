#include "Common.h"

//FilterCreate function declarations
void VS_CC remapCreate(const VSMap *in, VSMap *out, void *userData, VSCore *core, const VSAPI *vsapi);
void VS_CC remapSimpleCreate(const VSMap *in, VSMap *out, void *userData, VSCore *core, const VSAPI *vsapi);
void VS_CC replaceCreate(const VSMap *in, VSMap *out, void *userData, VSCore *core, const VSAPI *vsapi);

VS_EXTERNAL_API(void) VapourSynthPluginInit2(VSPlugin *plugin, const VSPLUGINAPI *vspapi) {
	vspapi->configPlugin("blaze.plugin.remap", "remap", "Remaps frame indices based on a file/string", VS_MAKE_VERSION(1, 1), VAPOURSYNTH_API_VERSION, 0, plugin);
	vspapi->registerFunction("RemapFrames", "baseclip:vnode;filename:data:opt;mappings:data:opt;sourceclip:vnode:opt;mismatch:int:opt;", "clip:vnode;", remapCreate, nullptr, plugin);
	vspapi->registerFunction("Remf", "baseclip:vnode;filename:data:opt;mappings:data:opt;sourceclip:vnode:opt;mismatch:int:opt;", "clip:vnode;", remapCreate, nullptr, plugin);
	vspapi->registerFunction("RemapFramesSimple", "clip:vnode;filename:data:opt;mappings:data:opt;", "clip:vnode;", remapSimpleCreate, nullptr, plugin);
	vspapi->registerFunction("Remfs", "clip:vnode;filename:data:opt;mappings:data:opt;", "clip:vnode;", remapSimpleCreate, nullptr, plugin);
	vspapi->registerFunction("ReplaceFramesSimple", "baseclip:vnode;sourceclip:vnode;filename:data:opt;mappings:data:opt;mismatch:int:opt;", "clip:vnode;", replaceCreate, nullptr, plugin);
	vspapi->registerFunction("Rfs", "baseclip:vnode;sourceclip:vnode;filename:data:opt;mappings:data:opt;mismatch:int:opt;", "clip:vnode;", replaceCreate, nullptr, plugin);
}
