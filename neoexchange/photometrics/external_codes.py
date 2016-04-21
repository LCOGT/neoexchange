'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2016-2016 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

import logging
import os
from subprocess import call

logger = logging.getLogger(__name__)

def setup_scamp_dir(source_dir, dest_dir):
    config_files = ['scamp_neox.cfg']

    if not os.path.exists(source_dir):
        logger.error("Source path '%s' does not exist" % source_dir)
        return -1

    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError:
            logger.error("Destination path '%s' could not be created" % dest_dir)
            return -2

    num_bad_links = 0
    for config in config_files:
        config_src_filepath = os.path.join(source_dir, config)
        config_dest_filepath = os.path.join(dest_dir, config)
        if not os.path.exists(config_dest_filepath):
            try:
                os.link(config_src_filepath, config_dest_filepath)
            except OSError:
                logger.error("Could not create link for %s to %s" % ( config, config_dest_filepath))
                num_bad_links += 1
    return_status = 0
    if num_bad_links > 0:
        return_status = -3
    return return_status
