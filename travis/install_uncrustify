#!/bin/bash

set -eux

uncrustifypkgs="$HOME/.cache/uncrustify_pkgs"
uncrustifyversion="0.63"
uncrustifydownload="uncrustify_${uncrustifyversion}-1_amd64.deb"
uncrustifyurl="https://s3.amazonaws.com/packages.citusdata.com/travis/${uncrustifydownload}"

# install travis uncrustify package
wget -N -P "${uncrustifypkgs}" "${uncrustifyurl}"
sudo dpkg --force-confdef --force-confold --install "${uncrustifypkgs}/${uncrustifydownload}"
