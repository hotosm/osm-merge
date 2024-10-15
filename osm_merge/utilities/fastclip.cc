//
// Copyright (c) 2024 OSM-US
//
// This file is part of Underpass.
//
//     This is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     Underpass is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with Underpass.  If not, see <https://www.gnu.org/licenses/>.
//

#include <cstdlib>
#include <vector>
#include <iostream>
#include <future>
#include <mutex>
#include <thread>
#include <string>

#include <ogr_geometry.h>

#include <boost/program_options.hpp>
#include <boost/filesystem.hpp>
#include <boost/log/trivial.hpp>
#include <boost/log/utility/setup/console.hpp>
#include <boost/log/core/core.hpp>
#include <boost/log/core/record.hpp>
#include <boost/log/core/record_view.hpp>
#include </usr/include/boost/log/utility/setup/file.hpp>
namespace logging = boost::log;

using namespace boost;
namespace opts = boost::program_options;

int
main(int argc, char *argv[])
{
    opts::positional_options_description p;
    opts::variables_map vm;
    opts::options_description desc("Allowed options");

    logging::add_file_log("clipfast.log");
    try {
        // clang-format off
        desc.add_options()
            ("help,h", "display help")
            ("infile,i", opts::value<std::string>(),
                        "Input data file"
                        "The file to be processed")
            ("verbose,v", "Enable verbosity")
            ("boundary,b", opts::value<std::string>(),
                "Boundary data file"
                "The boundary MultiPolygon to use for clipping");
            // clang-format on
            opts::store(opts::command_line_parser(argc, argv).options(desc).positional(p).run(), vm);
        opts::notify(vm);
    } catch (std::exception &e) {
        std::cout << e.what() << std::endl;
        return 1;
    }

    // By default, write everything to the log file
    logging::core::get()->set_filter(
        logging::trivial::severity >= logging::trivial::debug
        );

    if (vm.count("verbose")) {
        // Enable also displaying to the terminal
        logging::add_console_log(std::cout, boost::log::keywords::format = ">> %Message%");
    }
    
    BOOST_LOG_TRIVIAL(warning) << "An informational warning message";
    BOOST_LOG_TRIVIAL(error) << "An informational error message";
    BOOST_LOG_TRIVIAL(debug) << "An informational debug message";
    BOOST_LOG_TRIVIAL(info) << "An informational info message";

        // dbglogfile.setVerbosity();
    // }
    
}
// Local Variables:
// mode: C++
// indent-tabs-mode: nil
// End:
