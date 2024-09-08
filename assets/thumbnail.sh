#!/bin/bash

for i in *.jpg; do
    name=$(echo $i | sed -e "s/.jpg/.png/")
    jpegtopnm $i | pamscale -width 750 -height 600 | pamtopng > ${name}
done

