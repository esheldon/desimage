from __future__ import print_function
try:
    xrange
    is3=False
except:
    xrange=range
    is3=True

import sys
import os
import subprocess
import shutil
import numpy
from numpy import array, zeros, flipud, where, sqrt
import fitsio

from . import files

NOMINAL_EXPTIME=900.0

NONLINEAR=.12
DEFAULT_CAMPAIGN='y3a1_coadd'

def make_image_auto(campaign,
                    tilename,
                    rebin=None,
                    clean=True,
                    ranges=None,
                    type='jpg'):
    """
    make a color jpeg for the specified run

    parameters
    ----------
    campaign: string
        campaign, e.g. y3a1_coadd
    tilename: string
        DES coadd run
    rebin: int, optional
        Amount to rebin image
    """

    if isinstance(type,list):
        types=type
    else:
        types=[type]

    ifiles=FilesAuto(campaign, tilename, rebin=rebin)
    ifiles.sync()

    try:
        image_maker=RGBImageMaker(
            ifiles,
            rebin=rebin,
            ranges=ranges,
        )

        image_maker.make_image()

        for type in types:
            image_maker.write_image(image_type=type)
    finally:
        if clean:
            ifiles.clean()

def make_image_fromfiles(fname,
                         gfile,
                         rfile,
                         ifile,
                         campaign=DEFAULT_CAMPAIGN,
                         tilename='None',
                         ranges=None,
                         boost=None,
                         image_ext=1):
    """
    make a color jpeg for the specified run

    parameters
    ----------
    fname: string
        output image file name
    gfile: string
        file name for g band
    rfile: string
        file name for r band
    ifile: string
        file name for i band
    campaign: string, optional
        campaign, e.g. y3a1_coadd
    tilename: string, optional
        DES coadd run
    """

    if isinstance(type,list):
        types=type
    else:
        types=[type]

    ifiles=Files(
        gfile,
        rfile,
        ifile,
        campaign=campaign,
        tilename=tilename,
    )

    image_maker=RGBImageMaker(
        ifiles,
        image_ext=image_ext,
        ranges=ranges,
        boost=boost,
    )

    image_maker.make_image()

    image_maker.write_image(fname=fname)


class RGBImageMaker(object):
    """
    class to actually make the color image and write it
    """
    def __init__(self,
                 ifiles,
                 image_ext=1,
                 ranges=None,
                 boost=None,
                 rebin=None):

        self.ifiles=ifiles
        self.rebin=rebin
        self.boost=boost
        self.image_ext=image_ext
        self.ranges=ranges

        self.satval=1.0e9

    def _make_imlist(self):
        imlist=[]
        ifiles=self.ifiles
        for fname in [ifiles['gfile'], ifiles['rfile'], ifiles['ifile']]:
            print(fname)
            im = ImageTrans(
                fname,
                image_ext=self.image_ext,
                ranges=self.ranges,
                boost=self.boost,
            )
            imlist.append(im)

        for i,im in enumerate(imlist):
            #im.scale_image()
            im.flip_ud()
            #im.zero_bad_weightmap()
            #im.transpose()
            if self.rebin is not None:
                im.rebin(rebin)

            print()


        self.imlist=imlist

    def make_image(self):
        """
        create the rgb image
        """
        import images

        self._make_imlist()

        scales=self._get_scales()

        print("using satval:",self.satval)
        print('getting color image')
        imlist=self.imlist
        colorim=images.get_color_image(imlist[2].image,
                                       imlist[1].image,
                                       imlist[0].image,
                                       scales=scales,
                                       nonlinear=NONLINEAR,
                                       satval=self.satval)

        print('bytescaling')
        colorim = images.bytescale(colorim)

        self.colorim=colorim

    def write_image(self, image_type=None, fname=None):
        """
        write the image to an output file
        """
        from PIL import Image

        kw={}

        pim=Image.fromarray(self.colorim)

        if fname is not None:
            image_type=fname.split('.')[-1]
        else:
            assert image_type is not None,\
                'send image_type if fname is not sent'
            fname=self.ifiles.get_output_file(image_type)

        if image_type == 'jpg':
            kw['quality'] = 90

        print('writing:',fname)
        pim.save(fname, **kw)

    def _get_scales(self):
        """
        this will be i,r,g -> r,g,b
        """

        campaign=self.ifiles['campaign'].upper()
        print('getting scaled color for',campaign)

        # smaller scale means darker, so noise is more suppressed
        # compared to the peak. remember it is all scaled below
        # one, so we are also cutting off some point in the image


        if campaign=='ONEOFF':
            nominal_exptime=90.0
            # used for the big galaxy images
            SCALE=0.01
            relative_scales= array([1.0, 1.0, 1.5])
            #SCALE=0.004
            #SCALE=0.015
            #relative_scales= array([1.00, 1.2, 2.0])
            #relative_scales= array([1.0, 1.0, 1.6])
        elif campaign=='MACS':
            nominal_exptime=9000.0
            #SCALE=.015*sqrt(2.0)
            SCALE=0.015
            relative_scales= array([1.0, 1.0, 1.5])
        else:
            nominal_exptime=NOMINAL_EXPTIME
            if campaign=='Y3A1_COADD':
                SCALE=.015*sqrt(2.0)
                #SCALE=.010*sqrt(2.0)
                relative_scales= array([1.00, 1.2, 2.0])
            elif campaign=='Y1A1':
                print('getting scaled color for y1')
                SCALE=.010*sqrt(2.0)
                relative_scales= array([1.00, 1.2, 2.0])
            elif campaign=='SVA1':
                # SVA seems to require a very different scaling
                print('getting scaled color for sv')
                SCALE=.050*0.88
                relative_scales= array([1.00, 1.2, 2.5])
            else:
                raise ValueError("bad campaign: '%s'" % campaign)

        scales= SCALE*relative_scales

        for i in xrange(3):
            im=self.imlist[i]
            if im.exptime is not None:
                print("    scaling",im.band,im.exptime)
                scales[i] *= sqrt(nominal_exptime/im.exptime)
        return scales



class ImageTrans(object):
    def __init__(self, filename, boost=None, image_ext=1, ranges=None):
        import images
        self.ranges=ranges
        with fitsio.FITS(filename) as fits:
            if ranges is not None:
                rowslice, colslice = ranges
                print(rowslice)
                print(colslice)
                image=fits[image_ext][rowslice, colslice]

            else:
                image=fits[image_ext].read()

            if boost is not None:
                image = images.boost(image, boost)

            #image=fits[image_ext][12850:14820, 14000:17700]
            header=fits[image_ext].read_header()

        self.image=image
        self.header=header
        #self.weight=wt

        #self.band=header['FILTER'].split()[0]
        self.band=header.get('FILTER','None').split()[0]
        #self.exptime=header['exptime']
        self.exptime=header.get('exptime',NOMINAL_EXPTIME)

        #self.satval=header['saturate']
        #self.satval=header.get('saturate',1.e9)

    def zero_bad_weightmap(self, minval=0.001):
        print("    zeroing bad weight map")

        wt=self.weight
        w=where(wt < minval)

        if w[0].size > 0:
            print("        zeroing",w[0].size,"bad pixels")
            print("        max val from image:",self.image[w].max())
            self.image[w] = 0.0

    def flip_ud(self):
        print("    flipping",self.band)
        self.image = flipud(self.image)

    def transpose(self):
        print("    transposing",self.band)
        self.image = self.image.transpose()

    def rebin(self, rebin):
        import images
        print("    rebinning",self.band)
        image=self.image

        nrows,ncols=image.shape

        # pad nrows,ncols for rebin
        row_remain=(nrows % rebin)
        if row_remain != 0:
            nrows += (rebin-row_remain)
        col_remain=(ncols % rebin)
        if col_remain != 0:
            ncols += (rebin-col_remain)

        imrebin=zeros( (nrows, ncols), dtype='f4' )

        imrebin[0:image.shape[0], 0:image.shape[1]] = image[:,:]

        imrebin = images.rebin(imrebin, rebin)

        del self.image
        self.image=imrebin

    def scale_image(self, exptime=NOMINAL_EXPTIME):
        print('    scaling',self.band, self.exptime,"to",exptime)

        self.image *= (exptime/self.exptime)
        #self.image *= (exptime/self.exptime)



def make_dir(fname):
    dname=os.path.dirname(fname)
    if dname=='':
        return

    if not os.path.exists(dname):
        print('making dirs:',dname)
        os.makedirs(dname)


class FlistCache(dict):
    _flists={}

    def get_flist(self, campaign):
        """
        get the coadd file list
        """
        if campaign not in FlistCache._flists:
            flist_file=files.get_flist_file(campaign)
            print("reading:",flist_file)
            data=fitsio.read(flist_file)

            flist={}
            for i in xrange(data.size):
                key=_convert_bytes(data['key'][i].strip())
                path=_convert_bytes(data['path'][i].strip())
                flist[key] = path

            FlistCache._flists[campaign] = flist

        return FlistCache._flists[campaign]

def get_flist(campaign):
    """
    get the file list for this campaign
    """
    cache=FlistCache()
    return cache.get_flist(campaign)

class Files(dict):
    """
    hold file information
    """
    def __init__(self,
                 gfile,
                 rfile,
                 ifile,
                 campaign=DEFAULT_CAMPAIGN,
                 tilename='None'):

        self['campaign'] = campaign.upper()
        self['tilename'] = tilename
        self['gfile'] = gfile
        self['rfile'] = rfile
        self['ifile'] = ifile

class FilesAuto(Files):
    """
    deal with files, including syncing
    """

    def __init__(self, campaign, tilename, rebin=None, clean=True):
        self._bands=['g','r','i']

        self._rebin=rebin
        self._clean=clean

        fd=self._get_files()

        super(FilesAuto,self).__init__(
            fd['gfile'],
            fd['rfile'],
            fd['ifile'],
            campaign,
            tilename=tilename,
        )


    def get_remote_coadd_file(self, band):
        """
        local location of coadd fits file
        """
        return os.path.join(
            os.path.expandvars('$DESREMOTE_RSYNC'),
            self._get_coadd_path(band),
        )

    def get_coadd_file(self, band):
        """
        local location of coadd fits file
        """
        return os.path.join(
            self.get_temp_dir(),
            os.path.basename(self._get_coadd_path(band)),
        )

    def _get_coadd_path(self, band):
        """
        get local location for coadd file
        """
        flist=self.get_flist()

        key = '%s-%s' % (self['tilename'], band)
        return flist[key]


    def get_flist(self):
        """
        get the coadd file list
        """
        return get_flist(self['campaign'])

    def get_temp_dir(self):
        """
        temporary location for the input fits files
        """
        return files.get_temp_dir(
            self['campaign'],
            self['tilename'],
        )

    def get_output_dir(self):
        """
        location for the image and temp files
        """
        return files.get_output_dir(
            self['campaign'],
            self['tilename'],
        )

    def get_output_file(self, image_type):
        """
        location for the image and temp files
        """
        return files.get_output_file(
            self['campaign'],
            self['tilename'],
            rebin=self._rebin,
            ext=image_type,
        )


    def sync(self):
        """
        sync the coadd images
        """
        odir=self.get_temp_dir()
        if not os.path.exists(odir):
            os.makedirs(odir)

        remote_url=self.get_remote_coadd_file('g')
        remote_url = remote_url.replace('_g.fits','_[g,r,i].fits')
        cmd = r"""
    rsync                                   \
        -aP                                 \
        --password-file $DES_RSYNC_PASSFILE \
        %(remote_url)s \
        %(local_dir)s/
        """ % dict(
            remote_url=remote_url,
            local_dir=odir,
        )

        print(cmd)
        subprocess.check_call(cmd,shell=True)

    def clean(self):
        """
        clean up the source files
        """
        odir=self.get_temp_dir()
        if os.path.exists(odir):
            print("removing sources:",odir)
            shutil.rmtree(odir)

    def get_output_front(self):
        """
        location of a jpeg file
        """
        odir=self.get_output_dir()
        front='%(tilename)s_gri' % self

        if self._rebin is not None:
            front='%s_rebin%02d' % (front,int(self._rebin))
        return os.path.join(odir, front)

    def _get_files(self):

        d={}
        for band in self._bands:
            d['%sfile' % band] = self.get_coadd_file(band)
            d['%sfile_remote' % band] = self.get_remote_coadd_file(band)
        return d

def _convert_bytes(data):
    if is3:
        return str(data, 'utf-8')
    else:
        return str(data)
