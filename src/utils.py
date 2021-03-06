from subprocess import PIPE
from getpass import getuser
from colorama import Back
from signal import SIGTERM
from extension import *
import subprocess
import keyboard
import platform
import requests
import difflib
import zipfile
import tempfile
import hashlib
import click
import json
import sys
import os


index = 0
final_value = None


def get_architecture():
    if platform.machine().endswith('64'):
        return 'x64'
    if platform.machine().endswith('86'):
        return 'x32'


def get_download_url(architecture, pkg):
    if sys.platform == 'win32':
        if architecture == 'x64':
            return pkg['win64']
        elif architecture == 'x32':
            return pkg['win32']

    elif sys.platform == 'darwin':
        return pkg['darwin']

    elif sys.platform == 'linux':
        return pkg['debian']


def parse_json_response(pkg):
    return pkg['package-name'], pkg['source'], pkg['type'], pkg['switches']


def get_setup_name(download_type, package_name):
    if sys.platform == 'win32':
        download_path = tempfile.gettempdir()
        architecture = get_architecture()
        package = package_name.split()
        package.insert(0, download_path)
        package.append('Setup')
        package.append(architecture)
        package.append(download_type)
        return ''.join(package)

    elif sys.platform == 'darwin':
        download_path = tempfile.gettempdir()
        package = package_name.split()
        package.insert(0, download_path)
        package.append('Setup')
        package.append(download_type)
        return ''.join(package)

    elif sys.platform == 'linux':
        download_path = tempfile.gettempdir()
        package = package_name.split()
        package.insert(0, download_path)
        package.append('Setup')
        package.append(download_type)
        return ''.join(package)


def download(url, download_type: str, package_name, noprogress, silent):
    setup_name = get_setup_name(download_type, package_name)

    with open(setup_name, "wb") as f:
        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')

        if total_length is None:
            f.write(response.content)
        else:
            dl = 0
            full_length = int(total_length)

            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)

                if noprogress:
                    sys.stdout.write(
                        f"\r{round(dl / 1000000, 2)} / {round(full_length / 1000000, 2)} MB")
                    sys.stdout.flush()
                
                if silent:
                    pass
                
                elif not noprogress and not silent:
                    complete = int(50 * dl / full_length)
                    fill_c, unfill_c = chr(
                        9608) * complete, chr(9617) * (50 - complete)
                    sys.stdout.write(
                        f"\r|{fill_c}{unfill_c}| {round(dl / 1000000, 2)} / {round(full_length / 1000000, 2)} MB")
                    sys.stdout.flush()

    return get_setup_name(download_type, package_name)


def install_package(package_name, switches, download_type, no_color) -> str:
    file_name = get_setup_name(download_type, package_name)

    if sys.platform == 'win32':
        if download_type == '.exe':
            command = file_name + ' '
            for switch in switches:
                command = command + ' ' + switch
            try:
                proc = subprocess.call(command)

            except OSError as err:
                # Start Error Handling
                if '[WinError 740]' in str(err) and 'elevation' in str(err):
                    if not no_color:
                        click.echo(click.style(
                            'Administrator Elevation Required...', fg='red'))

                    if no_color:
                        click.echo(click.style(
                            'Administrator Elevation Required...'))

                if 'FileNotFoundError' in str(err):
                    click.echo(click.style(
                        'Silent Installation Failed With Exit Code 1.'))
                    click.echo(click.style(
                        'The Command Run During Installation Was Invalid Or The Installer Failed During The Installation Process.'))
                    click.echo(
                        'Raise A Support Ticket To www.electric.com/issue')
                    os._exit(0)

        elif download_type == '.msi':
            command = 'msiexec.exe /i' + file_name + ' '
            for switch in switches:
                command = command + ' ' + switch
            try:
                subprocess.call(command)
            except OSError:
                if not no_color:
                    click.echo(click.style(
                        'Administrator Elevation Required...', fg='bright_yellow'))
            os._exit(0)

        elif download_type == '.zip':
            if not no_color:
                click.echo(click.style(
                    f'Unzipping File At {file_name}', fg='green'))
            if no_color:
                click.echo(click.style(
                    f'Unzipping File At {file_name}'))

            zip_directory = fR'{tempfile.gettempdir()}\\{package_name}'
            with zipfile.ZipFile(file_name, 'r') as zip_ref:
                zip_ref.extractall(zip_directory)
            executable_list = []
            for name in os.listdir(zip_directory):
                if name.endswith('.exe'):
                    executable_list.append(name)
            executable_list.append('Exit')

            file_path = fR'{tempfile.gettempdir()}\\{package_name}'

            def trigger():
                click.clear()
                for executable in executable_list:
                    if executable == executable_list[index]:
                        print(Back.CYAN + executable + Back.RESET)
                    else:
                        print(executable)

            trigger()

            def up():
                global index
                if len(executable_list) != 1:
                    index -= 1
                    if index >= len(executable_list):
                        index = 0
                        trigger()
                        return
                    trigger()

            def down():
                global index
                if len(executable_list) != 1:
                    index += 1
                    if index >= len(executable_list):
                        index = 0
                        trigger()
                        return
                    trigger()

            def enter():
                if executable_list[index] == 'Exit':
                    os._exit(0)
                    return

                else:
                    path = file_path + "\\" + executable_list[index]
                    click.echo(click.style(
                        f'Running {executable_list[index]}. Hit Control + C to Quit', fg='magenta'))
                    subprocess.call(path, stdout=PIPE, stdin=PIPE, stderr=PIPE)
                    quit()

            keyboard.add_hotkey('up', up)
            keyboard.add_hotkey('down', down)
            keyboard.add_hotkey('enter', enter)
            keyboard.wait()

    # TODO: Implement the macOS side.
    if sys.platform == 'darwin':
        mount_dmg = f'hdiutil attach -nobrowse {file_name}'


def cleanup(download_type, package_name):
    setup_name = get_setup_name(download_type, package_name)
    command = 'del ' + setup_name
    subprocess.call(command, shell=True)


def run_uninstall(command: str, package_name, no_color):
    subprocess.Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
    if not no_color:
        click.echo(click.style(
            f"Successfully Uninstalled {package_name}", fg="bright_magenta"))
    if no_color:
        click.echo(click.style(
            f"Successfully Uninstalled {package_name}"))


def get_correct_package_names(res : str) -> list:
    package_names = []
    for package in res:
        # print('THSI IS THA PACKAGE', package)
        package_names.append(package)
    return package_names


def get_hash_algorithm(checksum: str):
    # A function to detect the hash algorithm used in checksum
    hashes = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}
    return hashes[len(checksum)] if len(checksum) in hashes else None


def get_checksum(bytecode: bytes, hash_algorithm: str):
    # A function to get the checksum from bytecode
    hash_type = getattr(hashlib, hash_algorithm, None)

    if hash_type:
        return hash_type(bytecode).hexdigest()

    return None


def send_req_all() -> dict:
    REQA = 'https://electric-packages-api.herokuapp.com/packages'
    time = 0.0
    response = requests.get(REQA, timeout=15)
    res = response.text.strip()
    time = response.elapsed.total_seconds()
    return json.loads(res), time


def get_pid(exe_name):
    proc = subprocess.Popen('tasklist', stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = proc.communicate()
    output = output.decode('utf-8')
    lines = output.splitlines()
    for line in lines:
        if exe_name in line:
            return line.split()[1]


def find_approx_pid(exe_name) -> str:
    proc = subprocess.Popen('tasklist', stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = proc.communicate()
    output = output.decode('utf-8')
    lines = output.splitlines()
    split_package_name = exe_name.split('-')

    cleaned_up_names = []
    for line in lines:
        try:
            cleaned_up_names.append(line.split()[0].strip('.exe'))
        except IndexError:
            continue

    matches = difflib.get_close_matches(exe_name, cleaned_up_names)

    if matches != []:
        for line in lines:
            if matches[0] in line:
                return line.split()[1]

    return 1


def handle_exit(status: str, setup_name : str, no_color : bool, quiet : bool):
    if status == 'Downloaded' or status == 'Installing' or status == 'Installed':
        exe_name = setup_name.split('\\')[-1]
        os.kill(int(get_pid(exe_name)), SIGTERM)

        write('SafetyHarness Successfully Created Clean Exit Gateway', 'green', no_color, quiet)
        write('\nRapidExit Using Gateway From SafetyHarness Successfully Exited With Code 0', 'light_blue', no_color, quiet)
        os._exit(0)
    
    if status == 'Got Download Path':
        write('\nRapidExit Successfully Exited With Code 0', 'green', no_color, quiet)
        os._exit(0)

    else:
        write('\nRapidExit Successfully Exited With Code 0', 'green', no_color, quiet)
        os._exit(0)


def kill_running_proc(package_name : str, quiet : bool, verbose : bool, debug : bool, yes : bool, no_color : bool):
    parts = package_name.split('-')
    name = ' '.join([p.capitalize() for p in parts])
    pid = int(find_approx_pid(package_name))
    if pid == 1:
        return
    if pid and pid != 1:
        if yes:
            write(f'Terminating {name}.', 'green', no_color, quiet)
            os.kill(pid, SIGTERM)
            return
        if quiet:
            os.kill(pid, SIGTERM)
            return
        terminate = click.prompt(f'Electric Detected {name} Running In The Background. Would You Like To Terminate It? [y/n]')
        if terminate == 'y':
            write(f'Terminating {name}.', 'green', no_color, quiet)
            os.kill(pid, SIGTERM)
        else:
            write('Aborting Installation!', 'red', no_color, quiet)
            write_verbose(f'Aborting Installation Due To {name} Running In Background', verbose, no_color, quiet)
            write_debug(f'Aborting Installation Due To {name} Running In Background. Process Was Not Terminated.', debug, no_color, quiet)
            os._exit(1)


def kill_proc(proc, no_color, silent):
    if proc is not None:
        proc.terminate()
        write('SafetyHarness Successfully Created Clean Exit Gateway', 'green', no_color, silent)
        write('\nRapidExit Using Gateway From SafetyHarness Successfully Exited With Code 0', 'light_blue', no_color, silent)
        os._exit(0)
    else:
        write('\nRapidExit Successfully Exited With Code 0', 'green', no_color, silent)
        os._exit(0)

def assert_cpu_compatible() -> int:
    cpu_count = os.cpu_count()
    print(cpu_count)

