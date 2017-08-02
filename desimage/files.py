import os

def get_list_dir():
    """
    we keep lists here
    """
    return os.path.expandvars('$DESDATA/jpg/lists')

def get_flist_file(campaign):
    """
    holds paths to coadds
    """
    dir=get_list_dir()
    fname='coadd-flist-%(campaign)s.fits' % dict(
        campaign=campaign.upper(),
    )
    return os.path.join(dir, fname)

def get_base_dir(campaign):
    """
    base directory
    """
    d='$DESDATA/jpg/%(campaign)s' % dict(
        campaign=campaign.upper(),
    )
    d=os.path.expandvars(d)
    return d


def get_output_dir(campaign, tilename):
    """
    location for the image and temp files
    """
    bdir=get_base_dir(campaign)

    return os.path.join(bdir, tilename)

def get_temp_dir(campaign, tilename):
    """
    location for the image and temp files
    """
    d = get_output_dir(campaign, tilename)
    return os.path.join(d, 'sources')

def get_output_file(campaign, tilename, rebin=None, ext='.jpg'):
    """
    location of a output file
    """
    odir=get_output_dir(campaign, tilename)

    parts = [
        tilename,
        'gri',
    ]

    if rebin is not None:
        parts += ['rebin%02d' % rebin]

    front = '-'.join(parts)
    fname = '%s.%s' % (front,ext)

    return os.path.join(odir, fname)

def get_log_file(campaign, tilename, rebin=None):
    """
    file holding log of processing
    """
    return get_output_file(
        campaign,
        tilename,
        rebin=rebin,
        ext='log',
    )
#
# batch processing
#

def get_script_dir(campaign):
    """
    location for scripts
    """
    bdir=get_base_dir(campaign)
    return os.path.join(bdir, 'scripts')

def get_script_file(campaign, tilename):
    """
    location for scripts
    """
    dir=get_script_dir(campaign)
    fname='%s.sh' % tilename
    return os.path.join(dir, fname)

def get_wq_file(campaign, tilename, missing=False):
    """
    location for scripts
    """
    dir=get_script_dir(campaign)
    parts=[tilename]
    if missing:
        parts += ['missing']

    fname='-'.join(parts)
    fname='%s.yaml' % fname
    return os.path.join(dir, fname)

def get_lsf_file(campaign, tilename, missing=False):
    """
    location for scripts
    """
    dir=get_script_dir(campaign)
    parts=[tilename]
    if missing:
        parts += ['missing']

    fname='-'.join(parts)
    fname='%s.lsf' % fname
    return os.path.join(dir, fname)
