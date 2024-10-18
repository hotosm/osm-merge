# Copyright (c) 2023 Humanitarian OpenStreetMap Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Humanitarian OpenStreetmap Team
# 1100 13th Street NW Suite 800 Washington, D.C. 20005
# <info@hotosm.org>
#

PACKAGE := org.tm-admin.py
NAME := tm-admin
VERSION := 0.1.0

all:
	@cd osm_merge ; $(MAKE)

apidoc: force
	cd docs && doxygen

clean:
	@cd tm_admin ; make clean

realclean:
	@cd tm_admin ; make clean

OSMIUM_FILES = $(shell find osmium-tool/src/ -type f -name '*.cpp' | sed -e 's/osmium-tool/../')

# FIXME: need to comment out line 319 so it'll compile
# osmium-tool/include/rapidjson/document.h

# Edit the cmake file for osmium-tool so it'll produce a shared library
# so it can be used in this project.
fixjson:
	status=$(shell cd osmium-tool && git status -s include/rapidjson/document.h | grep -c ' M '); \
	if test $$status -gt 0; then \
	    echo "The line that won't compile is remove"; \
	else \
	    sed '319d' include/rapidjson/document.h; \
	fi

libosmium-tool: fixjson
	if test ! -e osmium-tool; then \
	    echo "You need to checkout the osmium-tools sources"; \
	    exit 1; \
	fi
	status=$(shell cd osmium-tool && git status -s CMakeLists.txt | grep -c ' M '); \
	if test $$status -gt 0; then \
	    echo "CMakeLists.txt has already added the library"; \
	else \
	    sed -i '/^add_subdirectory(src)/a add_library("libosmium-tool" SHARED $(OSMIUM_FILES) )' osmium-tool/CMakeLists.txt; \
	fi
	if test ! -e osmium-tool/_build; then \
	    mkdir -p osmium-tool/_build; \
	fi
	cd osmium-tool/_build && cmake ..
	cd osmium-tool/_build && make # $(nproc --all)
force:
