#!/usr/bin/env python
#
# vmdktool.py - Helper for 'vmdktool'
#
# February 2015, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import logging
import os.path
import re
import shutil
from distutils.version import StrictVersion

from .helper import Helper

logger = logging.getLogger(__name__)


class VmdkTool(Helper):

    def __init__(self):
        super(VmdkTool, self).__init__("vmdktool")

    def _get_version(self):
        output = self.call_helper(['-V'])
        match = re.search("vmdktool version ([0-9.]+)", output)
        return StrictVersion(match.group(1))

    def install_helper(self):
        if self.find_helper():
            logger.warning("Tried to install {0} -- "
                           "but it's already available at {1}!"
                           .format(self.helper, self.helper_path))
            return
        if self.PACKAGE_MANAGERS['port']:
            self._check_call(['sudo', 'port', 'install', 'vmdktool'])
        elif self.PACKAGE_MANAGERS['apt-get'] or self.PACKAGE_MANAGERS['yum']:
            # We don't have vmdktool in apt or yum yet,
            # but we can build it manually:
            # vmdktool requires make and zlib
            if self.PACKAGE_MANAGERS['apt-get']:
                if not self.find_executable('make'):
                    self._check_call(['sudo', 'apt-get', 'install', 'make'])
                self._check_call(['sudo', 'apt-get', 'install', 'zlib1g-dev'])
            else:
                if not self.find_executable('make'):
                    self._check_call(['sudo', 'yum', 'install', 'make'])
                self._check_call(['sudo', 'yum', 'install', 'zlib-devel'])
            try:
                # Get the source
                self._check_call(['wget',
                                  'http://people.freebsd.org/~brian/'
                                  'vmdktool/vmdktool-1.4.tar.gz'])
                self._check_call(['tar', 'zxf', 'vmdktool-1.4.tar.gz'])
                # vmdktool is originally a BSD tool so it has some build
                # assumptions that aren't necessarily correct under Linux.
                # The easiest workaround is to override the CFLAGS to:
                # 1) add -D_GNU_SOURCE
                # 2) not treat all warnings as errors
                self._check_call(['make',
                                  'CFLAGS=-D_GNU_SOURCE -g -O -pipe',
                                  '--directory', 'vmdktool-1.4'])
                # TODO - this requires root
                if not os.path.exists('/usr/local/man/man8'):
                    try:
                        os.makedirs('/usr/local/man/man8', 493)  # 493 == 0o755
                    except OSError:
                        pass
                self._check_call(['make', '--directory',
                                  'vmdktool-1.4', 'install'])
            finally:
                if os.path.exists('vmdktool-1.4.tar.gz'):
                    os.remove('vmdktool-1.4.tar.gz')
                if os.path.exists('vmdktool-1.4'):
                    shutil.rmtree('vmdktool-1.4')
        else:
            raise NotImplementedError(
                "Unsure how to install vmdktool.\n"
                "See http://www.freshports.org/sysutils/vmdktool/")

    def convert_disk_image(self, file_path, output_dir,
                           new_format, new_subformat=None):
        """Convert the given disk image to the requested format/subformat.

        If the disk is already in this format then it is unchanged;
        otherwise, will convert to a new disk in the specified output_dir
        and return its path.

        Current supported conversions:

        * .vmdk (any format) to .vmdk (streamOptimized)
        * .img to .vmdk (streamOptimized)

        :param str file_path: Disk image file to inspect/convert
        :param str output_dir: Directory to place converted image into, if
          needed
        :param str new_format: Desired final format
        :param str new_subformat: Desired final subformat
        :return:
          * :attr:`file_path`, if no conversion was required
          * or a file path in :attr:`output_dir` containing the converted image

        :raise NotImplementedError: if the :attr:`new_format` and/or
          :attr:`new_subformat` are not supported conversion targets.
        """
        file_name = os.path.basename(file_path)
        (file_string, file_extension) = os.path.splitext(file_name)

        new_file_path = None

        if new_format == 'vmdk' and new_subformat == 'streamOptimized':
            new_file_path = os.path.join(output_dir, file_string + '.vmdk')
            logger.info("Invoking vmdktool to convert {0} to "
                        "stream-optimized VMDK {1}"
                        .format(file_path, new_file_path))
            # Note that vmdktool takes its arguments in unusual order -
            # output file comes before input file
            self.call_helper(['-z9', '-v', new_file_path, file_path])
        else:
            raise NotImplementedError("No support for converting disk image "
                                      "to format {0} / subformat {1}"
                                      .format(new_format, new_subformat))

        return new_file_path
