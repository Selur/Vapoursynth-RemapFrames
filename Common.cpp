#include "Common.h"

//Moves col to the next non-whitespace character.
//If there is no non-whitespace character, col will be equal to the size of the string.
void skipWhitespace(const std::string &str, int &col) {
	while (col < static_cast<int>(str.size()) && std::isspace(static_cast<unsigned char>(str[col]))) {
		++col;
	}
}

//Gets the first int from the position col in string str. 
//Example: getInt(" -4 5 6") will return -4.
int getInt(const std::string &str, int &col, const int &line, const bool &file, int maxFrames, Filter filter) {
	int initial{ col };
	
	//We check here for the character '-' to compensate for negative numbers.
	while (col < static_cast<int>(str.size()) && (std::isdigit(static_cast<unsigned char>(str[col])) || str[col] == '-')) {
		++col;
	}

	int frame;
	std::string filterName; //This string stores which filter we are calling getInt from. Used for exceptions.

	switch (filter) {
	case Filter::REMAP_FRAMES: filterName = "RemapFrames"; break;
	case Filter::REMAP_FRAMES_SIMPLE: filterName = "RemapFramesSimple"; break;
	case Filter::REPLACE_FRAMES_SIMPLE: filterName = "ReplaceFramesSimple"; break;
	}

	try {
		frame = std::stoi(str.substr(initial, col - initial)); //Trim the string to contain the part with a single integer and then convert
	}
	catch (const std::invalid_argument &) {
		//Catches the error thrown when the string cannot be converted to an int and throws a runtime error (Parse Error).
		std::string location{ file ? " text file " : " mappings "};
		std::string error{ filterName + ": Parse Error in" + location + "at line " + std::to_string(line + 1) + ", column " + std::to_string(col + 1) };
		throw std::runtime_error(error);
	}
	catch (const std::out_of_range &) {
		//Catches overflow exception and throws a runtime error (Overflow Error).
		std::string location{ file ? " text file " : " mappings " };
		std::string error{ filterName + ": Overflow Error in" + location + "at line " + std::to_string(line + 1) + ", column " + std::to_string(col + 1) };
		throw std::runtime_error(error);
	}
	if (frame < 0 || frame >= maxFrames) {
		//Checks if frame is out of bounds. If so, throws a runtime error (Index out of bounds).
		col = initial;
		std::string location{ file ? " text file " : " mappings " };
		std::string error{ filterName + ": Index out of bounds in" + location + "at line " + std::to_string(line + 1) + ", column " + std::to_string(col + 1) };
		throw std::runtime_error(error);
	}
	return frame;
}

//Returns the character in the string at position col. Returns 0 if col is out of bounds.
char getChar(const std::string &str, const int &col) {
	if (col < static_cast<int>(str.size()))
		return str[col];
	return 0;
}


//Fills a frame range. The method works like this:
//Get the first integer and store it in range.start -> Get the second integer and store it in range.end
// -> Check if the immediate non-whitespace character is ']'.
//If any of these fail (or are false), a runtime error (Parse Error) is thrown. 
void fillRange(const std::string &str, int &col, Range &range, const int &line, const bool &file, int maxFrames, Filter filter) {
	skipWhitespace(str, col);
	range.start = getInt(str, col, line, file, maxFrames, filter);

	skipWhitespace(str, col);
	range.end = getInt(str, col, line, file, maxFrames, filter);

	std::string filterName;

	switch (filter) {
	case Filter::REMAP_FRAMES: filterName = "RemapFrames"; break;
	case Filter::REMAP_FRAMES_SIMPLE: filterName = "RemapFramesSimple"; break;
	case Filter::REPLACE_FRAMES_SIMPLE: filterName = "ReplaceFramesSimple"; break;
	}

	skipWhitespace(str, col);
	if (col >= static_cast<int>(str.size()) || str[col] != ']') {
		std::string location{ file ? " text file " : " mappings " };
		std::string error{ filterName + ": Parse Error in" + location + "at line " + std::to_string(line + 1) + ", column " + std::to_string(col + 1) };
		throw std::runtime_error(error);
	}
	++col;
}

//Below code copied and modified from "reorderfilters.cpp" in VS repository.
//In API 4 variable dimensions are signalled by width/height of 0 and a variable
//format by a zeroed VSVideoFormat (colorFamily == cfUndefined).

MismatchCauses findCommonVi(VSVideoInfo *outVi, VSNode *node2, const VSAPI *vsapi) {
	MismatchCauses mismatch{ MismatchCauses::NO_MISMATCH };
	if (node2) {
		const VSVideoInfo *vi{ vsapi->getVideoInfo(node2) };

		if (outVi->width != vi->width || outVi->height != vi->height) {
			outVi->width = 0;
			outVi->height = 0;
			mismatch = MismatchCauses::DIFFERENT_DIMENSIONS;
		}

		else if (!vsh::isSameVideoFormat(&outVi->format, &vi->format)) {
			outVi->format = VSVideoFormat{};
			mismatch = MismatchCauses::DIFFERENT_FORMATS;
		}

		else if (outVi->fpsNum != vi->fpsNum || outVi->fpsDen != vi->fpsDen) {
			outVi->fpsDen = 0;
			outVi->fpsNum = 0;
			mismatch = MismatchCauses::DIFFERENT_FRAMERATES;
		}
		else if (outVi->numFrames != vi->numFrames) {
			if(outVi->numFrames < vi->numFrames)
				outVi->numFrames = vi->numFrames;
			mismatch = MismatchCauses::DIFFERENT_LENGTHS;
		}
	}
	return mismatch;
}
