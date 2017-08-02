from __future__ import print_function
import os
import subprocess

from . import imagemaker
from . import files

class ScriptMaker(object):
    def __init__(self, system, campaign, types, missing=False):
        self._system=system
        self._campaign=campaign
        self._missing=missing
        self._types=types

    def go(self):
        """
        write all scripts and batch files
        """
        script_dir=files.get_script_dir(self._campaign)
        if not os.path.exists(script_dir):
            print("making dir:",script_dir)
            os.makedirs(script_dir)

        flist = imagemaker.get_flist(self._campaign)

        tilenames={}
        for key in flist:
            tilename=key[0:-2]
            tilenames[tilename] = tilename
            
        for tilename in tilenames:

            if self._missing:
                dowrite=False
                for type in self._types:
                    image_file=files.get_output_file(
                        self._campaign,
                        tilename,
                        ext=type,
                    )
                    if not os.path.exists(image_file):
                        doprint=True
                        break
            else:
                doprint=True

            self._write_script(tilename)
            self._write_batch(tilename)

    def _write_batch(self, tilename):
        """
        write the appropriate batch file
        """
        if self._system=='wq':
            self._write_wq(tilename)
        elif self._system=='lsf':
            self._write_lsf(tilename)
        else:
            raise ValueError("Unsupported system: '%s'" % self._system)

    def _write_lsf(self, tilename):
        """
        write the wq script
        """
        lsf_file=files.get_lsf_file(
            self._campaign,
            tilename,
            missing=self._missing,
        )
        oefile=os.path.basename(lsf_file).replace('.lsf','.oe')
        script_file=files.get_script_file(
            self._campaign,
            tilename,
        )
        log_file=files.get_log_file(
            self._campaign,
            tilename,
        )
        job_name='%s-rgb' % tilename

        text="""#!/bin/bash
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

        if self._missing:
            subfile=lsf_file+'.submitted'
            if os.path.exists(subfile):
                os.remove(subfile)

        print("writing:",lsf_file)
        with open(lsf_file,'w') as fobj:
            fobj.write(text)

 
    def _write_wq(self, tilename):
        """
        write the wq script
        """
        wq_file=files.get_wq_file(
            self._campaign,
            tilename,
            missing=self._missing,
        )
        script_file=files.get_script_file(
            self._campaign,
            tilename,
        )
        log_file=files.get_log_file(
            self._campaign,
            tilename,
        )
        job_name='%s-rgb' % tilename

        text="""
command: |
    . $HOME/.bashrc
    source activate nsim

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

        if self._missing:
            wqlog=wq_file+'.wqlog'
            if os.path.exists(wqlog):
                os.remove(wqlog)

        print("writing:",wq_file)
        with open(wq_file,'w') as fobj:
            fobj.write(text)

    def _write_script(self, tilename):
        """
        write the basic script
        """

        script_file=files.get_script_file(
            self._campaign,
            tilename,
        )

        typestring=','.join(self._types)

        text="""
des-make-image --types=%(types)s %(campaign)s %(tilename)s
        \n"""
        text = text % dict(
            campaign=self._campaign,
            tilename=tilename,
            types=typestring,
        )

        print("writing:",script_file)
        with open(script_file,'w') as fobj:
            fobj.write(text)
