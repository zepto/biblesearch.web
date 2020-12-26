#!/usr/bin/env bash
# vim: sw=4:ts=4:sts=4:fdm=indent:fdl=0:
# -*- coding: UTF8 -*-
#
# A sword webapp.
# Copyright (C) 2012 Josiah Gordon <josiahg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

PYTHON=$(which python)
PYTHON_SITE_PACKAGES="$($PYTHON -c 'import site; print(site.getsitepackages()[0])')"
MODULE_DIR=$PYTHON_SITE_PACKAGES/biblesearch_web

pushd $MODULE_DIR
$PYTHON biblesearch_web.py
popd
