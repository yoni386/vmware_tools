import subprocess
import os
import sys
import glob
import re

build = '4.4.0-34'
vibs = ['mft-' + build, 'mft-int']

# gpath = '/vmfs/volumes/mswg/release/mft/mft-4.*.0/*/vmware/6.0/native_mft/driver/bundle/*'

gpath2 = '/vmfs/volumes/mswg/release/mft/mft-4.*.0/mft-{}/vmware/6.0/native_mft/driver/vib/*'.format(build)
paths = glob.glob(gpath2)

# vibs = paths

ls_exclude_vms = ['mft-oem-', 'mft-devel', 'mft-hpinst', 'mft-int']

vibs1 = [vib for vib in paths if vib not in vibs]
vibs1 = [vib for vib in paths if re.match('4.4.0-34', vib) and vib not in ls_exclude_vms]

for x in vibs1:
    print x

for x in paths:


args1 = ['du', '-h', '/bootbank/']
args2 = ['du', '-h', '/altbootbank/']
f = open('/tmp/chk_mft', 'w')
print('Number of vib: {}'.format(len(paths)))
numOfSuc = 0
numOfErr = 0

try:
    for path in paths:
        try:
            size = os.path.getsize(path)
            if size > 1024:
                size = os.path.getsize(path) / 1024 / 1024
            size_mb = str(size) + 'MB'
            path_split = path.split('/')[-1]
            print ('install: {}, vib size is: {}'.format(path_split, size_mb))
            p1 = subprocess.Popen(args1, stdout=subprocess.PIPE)
            result1 = p1.communicate()[0]
            p2 = subprocess.Popen(args2, stdout=subprocess.PIPE)
            result2 = p2.communicate()[0]
            result1 = result1.split('/')[0]
            result2 = result2.split('/')[0]
            str1 = 'vib: {0}, size: {1},  bootbank used size: {2} altbootbank used size: {3}'.format(path_split,
                                                                                                     size_mb,
                                                                                                     result1,
                                                                                                     result2)
            args3 = ['esxcli software vib install -d' + ' ' + path]

            try:
                p3 = subprocess.check_output(args3, shell=True)
                print('Success {}'.format(str1))
                f.write('Success {}'.format(str1))
                numOfSuc += 1
            except subprocess.CalledProcessError as err:
                numOfErr += 1
                print ('error code', err.cmd, err.output, numOfErr)
                f.write('\n' + '#' * 40)
                log = ('\nFailure vib: {0}'
                       '\nerror_cmd: {1}'
                       '\nerror_output: {2}'.format(path_split, err.cmd, err.output))
                f.write(log)

        except Exception as err:
            print (err)
            f.write('\n Failure {} error {}'.format(path.split('/')[-1], err))

        except KeyboardInterrupt:
            print ('Received interrupt, exit')
            sys.exit(1)

finally:
    print('Number of vib: {}'.format(len(paths)))
    print('Number of Success: {}'.format(numOfSuc))
    print('Number of Failure: {}'.format(numOfErr))
    f.write('\n' * 2)
    f.write('#' * 50)
    f.write('\nSummary;')
    f.write('\nNumber of Success: {} Number of Failure: {}'.format(numOfSuc, numOfErr))
    f.write('\nNumber of vib: {}'.format(len(paths)))
    f.write('\nTotal: {}'.format(numOfSuc + numOfErr))
    f.write('\n')
    f.close()


import subprocess
ret = subprocess.call(["ls", "-lah"]);

prog = subprocess.Popen(["ls", "-lah"], stdout=subprocess.PIPE)
errdata = prog.communicate()[1]

print (ret)
print (errdata)