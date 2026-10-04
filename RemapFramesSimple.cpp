#include "Common.h"

struct RemapSimpleData {
	VSNode *node;
	VSVideoInfo vi;
	std::vector<unsigned int> frameMap;
};

static const VSFrame *VS_CC remapSimpleGetFrame(int n, int activationReason, void *instanceData, void **frameData, VSFrameContext *frameCtx, VSCore *core, const VSAPI *vsapi) {
	RemapSimpleData *d{ static_cast<RemapSimpleData*>(instanceData) };

	if (activationReason == arInitial) {
		vsapi->requestFrameFilter(d->frameMap[n], d->node, frameCtx);
	}
	else if (activationReason == arAllFramesReady) {
		return vsapi->getFrameFilter(d->frameMap[n], d->node, frameCtx);
	}

	return nullptr;
}

static void VS_CC remapSimpleFree(void *instanceData, VSCore *core, const VSAPI *vsapi) {
	RemapSimpleData *d{ static_cast<RemapSimpleData*>(instanceData) };
	vsapi->freeNode(d->node);
	delete d;
}

//Checks for integers and keeps adding them to frameMap.
//There are two ways we could have done this:
//	1. Parse the entire file/string and set frameMap's size to the number of frames to avoid unnecessary resizing./..
//	   Parse the entire file/string again - this time to actually fill frameMap.
//	2. Resize frameMap on the go through push_back().
//We use method 2 here.
static void parse(std::string name, std::vector<unsigned int> &frameMap, void *stream, bool file, int maxFrames) {
	int line{ 0 };
	int col{ 0 };

	if (!file) {
		skipWhitespace(name, col);
		if (col == static_cast<int>(name.size()))
			throw std::runtime_error("RemapFramesSimple: Video length cannot be 0");
	}

	std::string temp;
	while (file ? std::getline(*static_cast<std::ifstream*>(stream), temp) : std::getline(*static_cast<std::stringstream*>(stream), temp)) {
		col = 0;
		while (col < static_cast<int>(temp.size())) {
			skipWhitespace(temp, col);
			char ch{ getChar(temp, col) };
			if (ch != 0) {
				if (ch == '#')
					break;
				else if (std::isdigit(static_cast<unsigned char>(ch)) || ch == '-')
					frameMap.push_back(getInt(temp, col, line, file, maxFrames, Filter::REMAP_FRAMES_SIMPLE));
				else {
					std::string location{ file ? " text file " : " mappings " };
					std::string error{ "RemapFramesSimple: Parse Error in" + location + "at line " + std::to_string(line + 1) + ", column " + std::to_string(col + 1) };
					throw std::runtime_error(error);
				}
			}
		}
		line++;
	}

	//API 4 requires a known, positive clip length.
	if (frameMap.empty())
		throw std::runtime_error("RemapFramesSimple: Video length cannot be 0");
}

void VS_CC remapSimpleCreate(const VSMap *in, VSMap *out, void *userData, VSCore *core, const VSAPI *vsapi) {
	RemapSimpleData d;
	d.node = vsapi->mapGetNode(in, "clip", 0, 0);
	d.vi = *vsapi->getVideoInfo(d.node);
	int err;

	std::string filename;
	const char* fn{ vsapi->mapGetData(in, "filename", 0, &err) };
	if (err)
		filename = "";
	else
		filename = fn;

	std::string mappings;
	const char* mp{ vsapi->mapGetData(in, "mappings", 0, &err) };
	if (err)
		mappings = "";
	else
		mappings = mp;

	if (mappings.empty() && filename.empty()) {
		vsapi->mapSetError(out, "RemapFramesSimple: Both filename and mappings cannot be empty");
		vsapi->freeNode(d.node);
		return;
	}
	else if (!mappings.empty() && !filename.empty()) {
		vsapi->mapSetError(out, "RemapFramesSimple: mappings and filename cannot be used together");
		vsapi->freeNode(d.node);
		return;
	}

	try {
		if (!filename.empty()) {
			std::ifstream file(filename);
			if (!file) {
				vsapi->mapSetError(out, "RemapFramesSimple: Failed to open the timecodes file.");
				vsapi->freeNode(d.node);
				return;
			}
			parse(filename, d.frameMap, &file, true, d.vi.numFrames);
		}
		else if (!mappings.empty()) {
			std::stringstream stream(mappings);
			parse(mappings, d.frameMap, &stream, false, d.vi.numFrames);
		}
	}
	catch (const std::exception &ex) {
		vsapi->mapSetError(out, ex.what());
		vsapi->freeNode(d.node);
		return;
	}

	d.vi.numFrames = static_cast<int>(d.frameMap.size());

	RemapSimpleData *data = new RemapSimpleData{ d };

	//Any input frame may be used any number of times.
	VSFilterDependency deps[] = { { data->node, rpGeneral } };
	vsapi->createVideoFilter(out, "RemapFramesSimple", &data->vi, remapSimpleGetFrame, remapSimpleFree, fmParallel, deps, 1, data, core);
}
