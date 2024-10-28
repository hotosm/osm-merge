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

// This is derived from osmium-tools, thanks you Jochen Topf for using
// the GPLv3! The osmium command tools are great, but I wanted something
// that could clip data and filter it focused on highways.

#include <cstdlib>
#include <vector>
#include <iostream>
#include <future>
#include <mutex>
#include <thread>
#include <string>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace fs = std::filesystem;

#include <gdal/ogr_geometry.h>
#include <gdal/ogrsf_frmts.h>

#include <boost/algorithm/string.hpp>
#include <boost/program_options.hpp>
#include <boost/log/trivial.hpp>
#include <boost/log/utility/setup/console.hpp>
#include <boost/log/core/core.hpp>
#include <boost/log/core/record.hpp>
#include <boost/log/core/record_view.hpp>
#include <boost/log/utility/setup/file.hpp>
namespace logging = boost::log;
using namespace boost;
namespace opts = boost::program_options;

#include <rapidjson/document.h>
#include <rapidjson/error/en.h>
#include <rapidjson/istreamwrapper.h>

#include <osmium/geom/coordinates.hpp>
#include <osmium/io/header.hpp>
#include <osmium/io/writer_options.hpp>
#include <osmium/osm.hpp>
#include <osmium/osm/box.hpp>
#include <osmium/util/progress_bar.hpp>
#include <osmium/util/string.hpp>
#include <osmium/util/verbose_output.hpp>
#include <osmium/handler/object_relations.hpp>
#include <osmium/geom/coordinates.hpp>
#include <osmium/memory/buffer.hpp>
#include <osmium/osm/location.hpp>
#include <osmium/index/map/sparse_mem_array.hpp>
#include <osmium/index/multimap/sparse_mem_array.hpp>
#include <osmium/builder/osm_object_builder.hpp>
#include <osmium/util/progress_bar.hpp>

#include <osmium/io/any_input.hpp>
#include <osmium/io/any_output.hpp>
#include <osmium/tags/taglist.hpp>
#include <osmium/tags/tags_filter.hpp>
#include <osmium/index/nwr_array.hpp>
#include <osmium/osm/entity_bits.hpp>
#include <osmium/osm/types.hpp>
#include <osmium/index/id_set.hpp>
#include <osmium/util/verbose_output.hpp>
#include <osmium/builder/osm_object_builder.hpp>
#include <osmium/handler/node_locations_for_ways.hpp>
#include <osmium/index/map/dense_file_array.hpp>
#include <osmium/index/map/sparse_file_array.hpp>

using namespace boost;
namespace opts = boost::program_options;

using index_type = osmium::index::map::SparseFileArray<osmium::unsigned_object_id_type, osmium::Location>;
//using index_type = osmium::index::map::DenseFileArray<osmium::unsigned_object_id_type, osmium::Location>;

using location_handler_type = osmium::handler::NodeLocationsForWays<index_type>;

struct MyHandler : public osmium::handler::Handler {

    // The callback functions can be either static or not depending on whether
    // you need to access any member variables of the handler.
    static void way(const osmium::Way& way) {
        std::cout << "way " << way.id() << "\n";
        for (const auto& nr : way.nodes()) {
            std::cout << "  node " << nr.ref() << " " << nr.location() << "\n";
        }
    }

}; // struct MyHandler

class GeoUtil
{
private:
    // FIXME: these should really be shared pointers
    // Only keep the outer polygons.
    std::map<std::string, const OGRGeometry *> outers;
    // std::shared_ptr<const OGRGeometry> boundaries;
    OGRMultiPolygon boundaries;
    osmium::nwr_array<osmium::TagsFilter> m_filters;
    osmium::nwr_array<osmium::index::IdSetDense<osmium::unsigned_object_id_type>> m_ids;
    bool m_invert_match = false;

public:
    GeoUtil(void) {
        GDALAllRegister();
    }

    void add_filter(osmium::osm_entity_bits::type entities, const osmium::TagMatcher& matcher) {
        if (entities & osmium::osm_entity_bits::node) {
            m_filters(osmium::item_type::node).add_rule(true, matcher);
        }
        if (entities & osmium::osm_entity_bits::way) {
            m_filters(osmium::item_type::way).add_rule(true, matcher);
        }
        if (entities & osmium::osm_entity_bits::relation) {
            m_filters(osmium::item_type::relation).add_rule(true, matcher);
        }
    }

     bool display_progress() const {
         // m_display_progress = display_progress_type::on_tty;
         // switch (m_display_progress) {
         //   case display_progress_type::on_tty:
         //       return osmium::util::isatty(2); // if STDERR is a TTY
         //   case display_progress_type::always:
         //       return true;
         //   default:
         //       break;
         // }
         // return false;
         return osmium::util::isatty(2);
     }

    void add_nodes(const osmium::Way& way) {
        for (const auto& nr : way.nodes()) {
            m_ids(osmium::item_type::node).set(nr.positive_ref());
        }
    }

    void copy_data(osmium::ProgressBar& progress_bar,
                   osmium::io::Reader& reader,
                   osmium::io::Writer& writer,
                   location_handler_type& location_handler) {
        while (osmium::memory::Buffer buffer = reader.read()) {
            progress_bar.update(reader.offset());
            osmium::apply(buffer, location_handler);

            if (true) {
                writer(std::move(buffer));
            } else {
                for (const auto& object : buffer) {
                    if (object.type() != osmium::item_type::node || !static_cast<const osmium::Node&>(object).tags().empty()) {
                        writer(object);
                    }
                }
            }
        }
    }

    bool filterFile(const std::string &infile,
                    const std::string &outfile) {
        // Filter anything not a highway.
        std::filesystem::path datafile = infile;
        if (!std::filesystem::exists(datafile)) {
            BOOST_LOG_TRIVIAL(error) << "File not found: " << datafile;
            return false;
        }

        std::string informat = std::filesystem::path(infile).extension();
        std::string outformat = std::filesystem::path(outfile).extension();
        
        const osmium::io::File input_file{infile, informat};
        const osmium::io::File output_file{outfile, outformat};
        
        try {
            // tell it to only read nodes and ways.
            osmium::io::Reader reader{infile, osmium::osm_entity_bits::way};
            osmium::io::Header header = reader.header();
            header.set("generator", "fastclip");
            osmium::io::Writer writer{"foobar.osm", header,
                osmium::io::overwrite::allow};

            osmium::TagsFilter hfilter{false};
            hfilter.add_rule(true, "highway", "path");
            hfilter.add_rule(true, "highway", "footway");
            hfilter.add_rule(true, "highway", "track");
            hfilter.add_rule(true, "highway", "unclassified");
            hfilter.add_rule(true, "highway", "residential");
            hfilter.add_rule(true, "highway", "tertiary");
            hfilter.add_rule(true, "highway", "primary");
            hfilter.add_rule(true, "highway", "secondary");

            // Get all ways matching the highway filter
            osmium::ProgressBar progress_bar1{reader.file_size(), display_progress()};
            while (osmium::memory::Buffer buffer = reader.read()) {
                progress_bar1.update(reader.offset());
                // for (const auto& object : buffer.select<osmium::OSMObject>()) {
                for (const auto& way : buffer.select<osmium::Way>()) {
                    if (osmium::tags::match_any_of(way.tags(), hfilter)) {
                        // Cache the node refs
                        add_nodes(way);
                        writer(way);
                    }
                }
            }
            writer.close();
            // FIXME: I'm not sure if we can reuse the reader
            reader.close();
            progress_bar1.done();

            // Now get the nodes that are referenced by the ways.
            osmium::ProgressBar progress_bar2{reader.file_size(), display_progress()};
            const auto& map_factory = osmium::index::MapFactory<osmium::unsigned_object_id_type, osmium::Location>::instance();
            std::string default_index_type{ map_factory.has_map_type("sparse_mmap_array") ? "sparse_mmap_array" : "sparse_mem_array" };

            osmium::io::Reader reader2{"foobar.osm", osmium::osm_entity_bits::way};
            const int fd = ::open(infile.c_str(), O_RDWR);
            if (fd == -1) {
                BOOST_LOG_TRIVIAL(error) << "Can not open location cache file '" << infile << "': " << std::strerror(errno);
                return 1;
            }            
            index_type index{fd};
            location_handler_type location_handler{index};
            MyHandler handler;
            osmium::apply(reader2, location_handler, handler);

            // Explicitly close input so we get notified of any errors.
            reader.close();
#if 0
            osmium::io::Reader nreader{outfile, osmium::osm_entity_bits::node};
            while (osmium::memory::Buffer buffer = nreader.read()) {
                progress_bar2.update(nreader.offset());
                for (const auto& object : buffer.select<osmium::OSMObject>()) {
                    if (m_ids(object.type()).get(object.positive_id())) {
                        writer(object);
                    }
                }
            }
            progress_bar2.done();
#endif
#if 0
            BOOST_LOG_TRIVIAL(debug) << "Copying input file '" << infile << "'\n";
            osmium::io::Reader reader{infile};
            osmium::io::Header header{reader.header()};
            setup_header(header);
            osmium::io::Writer writer(outfile, header, m_output_overwrite, m_fsync);
            
            osmium::ProgressBar progress_bar{reader.file_size(), display_progress()};
            copy_data(progress_bar2, reader, writer, location_handler);
            progress_bar2.done();

#endif
            writer.close();
            reader.close();
            BOOST_LOG_TRIVIAL(info) << "Wrote " << outfile;
        } catch (const std::exception& e) {
            // All exceptions used by the Osmium library derive from std::exception.
            BOOST_LOG_TRIVIAL(error)  << e.what();
            return false;
        }

        return true;
    }

    bool writeOuters(const std::string &filespec) {
        BOOST_LOG_TRIVIAL(debug) << "There are " <<  outers.size() << " outer boundaries" ;
        // Set the SRS to avoid problems later.
        OGRSpatialReference* poSRS = new OGRSpatialReference();
        poSRS->importFromEPSG(4326);

        GDALDriver *driver = (GDALDriver *)GDALGetDriverByName("GeoJson");
        // auto poDS = (GDALDataset*) GDALOpenEx( "point.geojson", GDAL_OF_VECTOR, NULL, NULL, NULL );

        fs::path foo(filespec);
        // GDAL can't overwrite GeoJson files.
        if (std::filesystem::exists(filespec)) {
            std::filesystem::remove(filespec);
        }
        GDALDataset *poDS = driver->Create(filespec.c_str(), 0, 0, 0, GDT_Unknown, NULL );
        auto layer = poDS->CreateLayer( "boundaries", NULL, wkbMultiPolygon, NULL );
        // The only field is the
        OGRFieldDefn oField("Name", OFTString);
        oField.SetWidth(128);
        layer->CreateField(&oField);

        // Each entry
        for (auto it = outers.begin(); it!= outers.end(); ++it) {
            OGRFeature *feature = OGRFeature::CreateFeature(layer->GetLayerDefn());
            feature->SetField("name", it->first.c_str());
            int result = layer->CreateFeature(feature);
            // BOOST_LOG_TRIVIAL(debug) << "Regions: " << it->second.getGeometryName();
            // feature->SetSpatialRef(poSRS);

            // Clean to avoid memory leaks
            OGRFeature::DestroyFeature(feature);
        }
        // Clean to avoid memory leaks
        poSRS->Release();
        poDS->Close();
        
        return true;
    }

    // CPLSetConfigOption( "OGR_GEOJSON_MAX_OBJ_SIZE", "0" );
    bool readAOI(const std::string &filespec) {
        /// This reads in a MultiPolygon files of boundaries. Each
        // boundary may itself be a MultiPolygon, but we don't
        // want the inner polygons, so extract just those.







        // std::filesystem::path boundary_file = filespec;
        // if (!std::filesystem::exists(boundary_file)) {
        //     BOOST_LOG_TRIVIAL(error) << "File not found: " << boundary_file;
        //     return false;
        // }
        // BOOST_LOG_TRIVIAL(info) << "Opening geo data file: "<< boundary_file;
        // std::string file = boundary_file.string();
        // GDALDataset *poDS = (GDALDataset *)GDALOpenEx(file.c_str(),
        //                    GDAL_OF_VECTOR | GDAL_OF_VERBOSE_ERROR, NULL, NULL, NULL);
        // if (poDS == 0) {
        //     BOOST_LOG_TRIVIAL(error) << "couldn't open " << boundary_file;
        //     return false;
        // }
        // // layer = poDS->GetLayerByName(boundary_file.stem().c_str());

        // BOOST_LOG_TRIVIAL(debug) << poDS->GetLayerCount();
        // auto layer = poDS->GetLayerByName("boundaries");
        // // OGRFeatureDefn *poFDefn = layer->GetLayerDefn();
        // // auto layer = poDS->GetLayer(0);
        // if (layer == 0) {
        //     BOOST_LOG_TRIVIAL(error) << "Couldn't get layer " << boundary_file.stem();
        //     return false;
        // }
        // // BOOST_LOG_TRIVIAL(error) << "Get Feature Count " << layer->GetFeatureCount();
        
        // if (layer != 0) {
        //     for (auto &feature : layer) {
        //         // Each feature is an administrative region
        //         std::string name;
        //         double area;
        //         // BOOST_LOG_TRIVIAL(debug) << "Processing feature ";
        //         int foo = feature->GetFieldIndex("FORESTNAME");
        //         // BOOST_LOG_TRIVIAL(debug) << "Fields :" << feature.GetFieldCount();
        //         for (auto &field : feature) {
        //             if (boost::iequals(field.GetName(), "FORESTNAME")) {
        //                 name = field.GetAsString();
        //                 // BOOST_LOG_TRIVIAL(debug) << "Processing field " << name;
        //             }
        //             // Ignore really tiny shapes
        //             // if (boost::iequals(field.GetName(), "SHAPE_Area")) {
        //             //     area = field.GetAsDouble();
        //             //     BOOST_LOG_TRIVIAL(debug) << " " << area;
        //             // }
        //             // Ignore really tiny shapes
        //             // if (boost::iequals(field.GetName(), "GIS_ACRES")) {
        //             //     area = field.GetAsDouble();
        //             //     BOOST_LOG_TRIVIAL(debug) << " " << area;
        //             // }
        //         }

        //         // The entire file is a big MultiPolygon, each region
        //         // is the next layer down.
        //         const OGRGeometry *geom = feature->GetGeometryRef();
        //         const OGRMultiPolygon *mp = geom->toMultiPolygon();
        //         BOOST_LOG_TRIVIAL(debug) << "Entries: " << mp->getNumGeometries();
        //         for (auto &region : mp) {
        //             // FIXME: this is probably unnecessary, as it appears it's
        //             // always a polygon which defeats the attempt to
        //             // delete all the inners.
        //             // BOOST_LOG_TRIVIAL(debug) << "FOO! " << region->getGeometryName();
        //             auto poly = region->getExteriorRing();
        //             outers[name] = poly;
        //             boundaries.addGeometry(poly);
        //         }
        //     }
        // }
        return true;
    }    
};

int
main(int argc, char *argv[])
{
    opts::positional_options_description p;
    opts::variables_map vm;
    opts::options_description desc("Allowed options");

    logging::add_file_log("fastclip.log");
    try {
        // clang-format off
        desc.add_options()
            ("help,h", "display help")
            ("verbose,v", "Enable verbosity")
            ("infile,i", opts::value<std::string>(), "Input data file"
                        "The file to be processed")
            ("outfile,o", opts::value<std::string>(), "Output data file"
                "The output boundaries MultiPolygon")
            ("filter,f", "Filter for only highways")
            ("boundary,b", opts::value<std::string>(), "Boundary data file"
             "The boundary MultiPolygon to use for clipping");
            // clang-format on
            opts::store(opts::command_line_parser(argc, argv).options(desc).positional(p).run(), vm);
        opts::notify(vm);
    } catch (std::exception &e) {
        std::cout << e.what() << std::endl;
        return 1;
    }

    opts::store(opts::command_line_parser(argc, argv).options(desc).positional(p).run(), vm);
    opts::notify(vm);

    // By default, write everything to the log file
    logging::core::get()->set_filter(
        logging::trivial::severity >= logging::trivial::debug
        );

    if (vm.count("verbose")) {
        // Enable also displaying to the terminal
        logging::add_console_log(std::cout, boost::log::keywords::format = ">> %Message%");
    }

    auto geoutil = GeoUtil();
    if (vm.count("filter")) {
        if (vm.count("infile") && vm.count("outfile")) {
            std::string infile = vm["infile"].as<std::string>();
            std::string outfile = vm["outfile"].as<std::string>();
            geoutil.filterFile(infile, outfile);
        }
        exit(0);
    }

    if (vm.count("boundary")) {
        std::string filespec = vm["boundary"].as<std::string>();
        geoutil.readAOI(filespec);
    }

    if (vm.count("outfile")) {
        std::string filespec = vm["outfile"].as<std::string>();
        geoutil.writeOuters(filespec);
        BOOST_LOG_TRIVIAL(info) << "Wrote output file " << filespec;
    }

    BOOST_LOG_TRIVIAL(warning) << "An informational warning message";
    BOOST_LOG_TRIVIAL(error) << "An informational error message";
    BOOST_LOG_TRIVIAL(debug) << "An informational debug message";
    BOOST_LOG_TRIVIAL(info) << "An informational info message";
}

// class MyHandler : public osmium::handler::Handler {
// public:
//     void way(const osmium::Way& way) {
//         std::cout << "way " << way.id() << '\n';
//         for (const auto& n : way.nodes()) {
//             std::cout << n.ref() << ": " << n.lon() << ", " << n.lat() << '\n';
//         }
//     }
// };

// Local Variables:
// mode: C++
// indent-tabs-mode: nil
// End:
