#!/bin/bash
set -e
# script to automatically generate the psyplot api documentation using
# sphinx-apidoc and sed
sphinx-apidoc -f -M -e  -T -o api ../psy_view/
# replace chapter title in psyplot.rst
sed -i -e '1,1s/.*/API Reference/' api/psy_view.rst

sphinx-autogen -o generated *.rst */*.rst
