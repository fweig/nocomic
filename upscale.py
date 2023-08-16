from zipfile import (
        ZipFile,
)

from argparse import (
        ArgumentParser,
)

import shutil
import subprocess
import logging as log
import os

def unpack(zip_file, output_dir):
    log.debug('Unpacking {} to {}'.format(zip_file, output_dir))
    with ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

def create_archive(zip_file, input_dir):
    log.debug('Creating archive {} from {}'.format(zip_file, input_dir))
    shutil.make_archive(zip_file, 'zip', input_dir)

def run_upscaler(upscaler, input_dir, output_dir):
    log.debug('Running upscaler "{}" on "{}" and writing to "{}"'.format(upscaler, input_dir, output_dir))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    upscale_call = "{} -i '{}' -o '{}'".format(upscaler, input_dir, output_dir)
    log.debug('Running command "{}"'.format(upscale_call))
    subprocess.run([upscaler, '-i', input_dir, '-o', output_dir], shell=False, check=True, capture_output=True)

    # iterate subdirectories and run upscaler on them
    for subdir in os.listdir(input_dir):
        subdir_path = os.path.join(input_dir, subdir)
        if os.path.isdir(subdir_path):
            upscale_output = os.path.join(output_dir, subdir)
            run_upscaler(upscaler, subdir_path, upscale_output)


def main():

    parser = ArgumentParser()
    parser.add_argument('-i', '--input', help='Input directory', required=True)
    parser.add_argument('-u', '--upscaler', help='Upscaler to use', default=os.path.join('waifu2x-ncnn-vulkan', 'waifu2x-ncnn-vulkan.exe'))
    parser.add_argument('-v', '--verbose', help='verbose logging', action='store_true', default=False)

    args = parser.parse_args()
    input_dir = args.input
    tmpdir = args.input + '_tmp'
    output_dir = args.input + '_upscaled'

    loglevel = log.DEBUG if args.verbose else log.INFO
    log.basicConfig(level=loglevel, format='%(levelname)s:%(asctime)s: %(message)s')

    log.info('Upscaling images in {}'.format(input_dir))
    log.info('Writing output to dir {}'.format(output_dir))

    # create tmp dir
    # fail on purpose here, if directory already exists so we don't delete any user files by accident
    log.debug('Creating tmp dir {}'.format(tmpdir))
    os.makedirs(tmpdir)

    # unpack all files in input directory
    files = os.listdir(input_dir)
    files.sort() # sort files by name

    for file in files:
        archive_file = os.path.join(input_dir, file)
        ext = os.path.splitext(file)[1]
        if ext not in ['.zip', '.cbz']:
            log.debug('Skipping file {} with extension {}'.format(file, ext))
            continue
        unpacked_dir = os.path.join(tmpdir, os.path.splitext(file)[0])
        log.info("Unpack '{}'".format(archive_file))
        unpack(archive_file, unpacked_dir)

        # run upscaler on unpacked dir
        upscale_output = unpacked_dir + '_upscaled'
        log.info("Run upscaler")
        run_upscaler(args.upscaler, unpacked_dir, upscale_output)

        log.info("Create upscaled archive '{}'".format(file))
        upscaled_archive = os.path.join(output_dir, file)
        create_archive(upscaled_archive, upscale_output)

    # cleanup tmp dir
    log.debug('Cleaning up tmp dir {}'.format(tmpdir))
    shutil.rmtree(tmpdir)

if __name__ == '__main__':
    main()
