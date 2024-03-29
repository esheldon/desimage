from __future__ import print_function
import os

from . import imagemaker
from . import files


class ScriptMaker(object):
    def __init__(self, system, types=None, bands=None, campaign=None):
        self._system = system

        if campaign is None:
            campaign = imagemaker.DEFAULT_CAMPAIGN

        if types is None:
            types = ["jpg"]
        elif not isinstance(types, (list, tuple)):
            types = [types]

        if bands is None:
            bands = ["g", "r", "i"]

        self._campaign = campaign
        self._types = types
        self._bands = bands

    def go(self):
        """
        write all scripts and batch files
        """
        script_dir = files.get_script_dir(self._campaign)
        if not os.path.exists(script_dir):
            print("making dir:", script_dir)
            os.makedirs(script_dir)

        flist = imagemaker.get_flist(self._campaign)

        tilenames = {}
        for key in flist:
            tilename = key[0:-2]
            tilenames[tilename] = tilename

        for tilename in tilenames:

            # make sure all bands are present
            if not self._bands_present(tilename, flist):
                continue

            doprint = False
            for type in self._types:
                image_file = files.get_output_file(
                    self._campaign,
                    tilename,
                    self._bands,
                    ext=type,
                )
                if not os.path.exists(image_file):
                    doprint = True
                    break

            if doprint:
                self._write_script(tilename)
                self._write_batch(tilename)
            else:
                self._clear_batch(tilename)

    def _bands_present(self, tilename, flist):
        for band in self._bands:
            key = "%s-%s" % (tilename, band)
            if key not in flist:
                print("missing %s" % key)
                return False

        return True

    def _write_batch(self, tilename):
        """
        write the appropriate batch file
        """
        if self._system == "wq":
            self._write_wq(tilename)
        elif self._system == "lsf":
            self._write_lsf(tilename)
        else:
            raise ValueError("Unsupported system: '%s'" % self._system)

    def _clear_batch(self, tilename):
        """
        write the appropriate batch file
        """
        if self._system == "wq":
            self._clear_wq(tilename)
        elif self._system == "lsf":
            self._clear_lsf(tilename)
        else:
            raise ValueError("Unsupported system: '%s'" % self._system)

    def _clear_wq(self, tilename):
        wq_file = files.get_wq_file(
            self._campaign,
            tilename,
            self._bands,
        )
        wq_log = wq_file + ".wqlog"

        flist = [wq_file, wq_log]
        for f in flist:
            if os.path.exists(f):
                os.remove(f)

    def _write_lsf(self, tilename):
        """
        write the wq script
        """
        lsf_file = files.get_lsf_file(
            self._campaign,
            tilename,
            self._bands,
        )
        oefile = os.path.basename(lsf_file).replace(".lsf", ".oe")
        script_file = files.get_script_file(
            self._campaign,
            tilename,
        )
        job_name = "%s-rgb" % tilename

        text = """#!/bin/bash
#BSUB -J "%(job_name)s"
#BSUB -oo ./%(oefile)s
#BSUB -n 2
#BSUB -R span[hosts=1]
#BSUB -R "linux64 && rhel60 && (!deft)"
#BSUB -W 25

bash %(script_file)s \n"""

        text = text % dict(
            script_file=script_file,
            job_name=job_name,
            oefile=oefile,
        )

        print("writing:", lsf_file)
        with open(lsf_file, "w") as fobj:
            fobj.write(text)

    def _write_wq(self, tilename):
        """
        write the wq script
        """
        wq_file = files.get_wq_file(
            self._campaign,
            tilename,
            self._bands,
        )
        wqlog = wq_file + ".wqlog"

        script_file = files.get_script_file(
            self._campaign,
            tilename,
            self._bands,
        )
        log_file = files.get_log_file(
            self._campaign,
            tilename,
            self._bands,
        )
        job_name = "%s-rgb" % tilename

        text = """
command: |
    . $HOME/.bashrc
    source activate y5color

    log_file=%(log_file)s
    rm -f $log_file

    log_dir=$(dirname $log_file)
    log_base=$(basename $log_file)

    mkdir -vp $log_dir

    log_tmp="$TMPDIR/$log_base"
    bash %(script_file)s &> $log_tmp

    mv -vf $log_tmp $log_file

mode: bynode
job_name: "%(job_name)s"
        \n"""

        text = text % dict(
            log_file=log_file,
            script_file=script_file,
            job_name=job_name,
        )

        if os.path.exists(wqlog):
            os.remove(wqlog)

        print("writing:", wq_file)
        with open(wq_file, "w") as fobj:
            fobj.write(text)

    def _write_script(self, tilename):
        """
        write the basic script
        """

        bstr = ",".join(self._bands)

        script_file = files.get_script_file(
            self._campaign,
            tilename,
            self._bands,
        )

        typestring = ",".join(self._types)

        text = """
des-make-image --types=%(types)s --campaign=%(campaign)s --bands=%(bands)s %(tilename)s
        \n"""  # noqa
        text = text % dict(
            campaign=self._campaign,
            tilename=tilename,
            types=typestring,
            bands=bstr,
        )

        print("writing:", script_file)
        with open(script_file, "w") as fobj:
            fobj.write(text)
