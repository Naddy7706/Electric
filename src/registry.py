import errno, os, winreg
from typing import final
import difflib

keys : list = []

def get_uninstall_key(package_name : str):
    def get_registry_info():
        proc_arch = os.environ['PROCESSOR_ARCHITECTURE'].lower()
        proc_arch64 = None if 'PROCESSOR_ARCHITEW6432' not in os.environ.keys() else os.environ['PROCESSOR_ARCHITEW6432'].lower()
        if proc_arch == 'x86' and not proc_arch64:
            arch_keys = {0}
        elif proc_arch == 'x86' or proc_arch == 'amd64':
            arch_keys = {winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY}
        else:
            raise OSError("Unhandled arch: %s" % proc_arch)
        
        for arch_key in arch_keys:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, R"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0, winreg.KEY_READ | arch_key)
            for i in range(0, winreg.QueryInfoKey(key)[0]):
                skey_name = winreg.EnumKey(key, i)
                skey = winreg.OpenKey(key, skey_name)
                try:
                    name = winreg.QueryValueEx(skey, 'DisplayName')[0]
                    stro = winreg.QueryValueEx(skey, 'UninstallString')[0]
                
                    url, loc, pub = None, None, None
                    try:
                        url = winreg.QueryValueEx(skey, 'URLInfoAbout')[0]
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            pass
                    try:  
                        loc = winreg.QueryValueEx(skey, 'InstallLocation')[0]
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            pass
                    try:
                        pub = winreg.QueryValueEx(skey, 'Publisher')[0]
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            pass
                    qstro = None
                    if 'MsiExec.exe' in stro:
                        qstro = stro + ' /quiet'
                    try:
                        qstro = winreg.QueryValueEx(skey, 'QuietUninstallString')[0]
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            pass
                    if qstro is not None:
                        gen_dict : dict = {
                            "DisplayName": name,
                            "QuietUninstallString": qstro,
                            "URLInfoAbout": url,
                            "InstallLocation": loc,
                            "Publisher": pub,
                        }

                        keys.append(gen_dict)
                    else:
                        gen_dict : dict = {
                            "DisplayName": name,
                            "UninstallString": stro,
                            "URLInfoAbout": url,
                            "InstallLocation": loc,
                            "Publisher": pub,
                        }
                        keys.append(gen_dict)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        pass
                finally:
                    skey.Close()

    final_array = []
    total = []
    def get_uninstall_string(package_name : str):
        nonlocal final_array
        string_gen(package_name)

        for key in keys:
            display_name = key['DisplayName']
            url = None if 'URLInfoAbout' not in key else key['URLInfoAbout']
            uninstall_string = '' if 'UninstallString' not in key else key['UninstallString']
            quiet_uninstall_string = '' if 'QuietUninstallString' not in key else key['QuietUninstallString']
            install_location = '' if 'InstallLocation' not in key else key['InstallLocation']
            final_list = [display_name, url, uninstall_string, quiet_uninstall_string, install_location]
            index = 0
            matches = None
            refined_list = []

            for object in final_list:
                if object is None:
                    final_list.pop(index)
                if object is not None:
                    name = object.lower()
                refined_list.append(name)
                index += 1

            for string in strings:
                matches = difflib.get_close_matches(string, refined_list)
                if matches == []:
                    possibilities = []
                    for element in refined_list:
                        for string in strings:
                            if string in element:
                                possibilities.append(key)
                    if possibilities != []:
                        total.append(possibilities)
                    else:
                        continue
                else:
                    final_array.append(key)


    strings = []
    def string_gen(package_name : str):
        # Split by `-`
        split1 = package_name.split('-')
        strings.append(''.join(split1))

    def get_more_accurate_matches(return_array):
        confidence = 50
        index : int = 0
        final_index = None
        final_confidence = None 
        for key in return_array:
            name = key['DisplayName']
            loc = key['InstallLocation']
            uninstall_string = None if 'UninstallString' not in key else key['UninstallString']
            quiet_uninstall_string = None if 'QuietUninstallString' not in key else key['QuietUninstallString']
            url = None if 'URLInfoAbout' not in key else key['URLInfoAbout']
            for string in strings:
                if name is not None:
                    if string.lower() in name or string.upper() in name or string.capitalize() in name:
                        confidence += 10
                if loc is not None:
                    if string.lower() in loc or string.upper() in loc or string.capitalize() in loc:
                        
                        confidence += 5
                if uninstall_string is not None:
                    if string.lower() in uninstall_string or string.upper() in uninstall_string or string.capitalize() in uninstall_string:
                        confidence += 5
                if quiet_uninstall_string is not None:
                    if string.lower() in quiet_uninstall_string or string.upper() in quiet_uninstall_string or string.capitalize() in quiet_uninstall_string:
                        confidence += 5
                if url is not None:
                    if string.lower() in url or string.upper() in url or string.capitalize() in url:
                        confidence += 10
                if final_confidence == confidence:
                    # Unjoin words
                    word_list = package_name.split('-')
                    for word in word_list:
                        if name is not None:
                            if word in name:
                                confidence += 5
                        if word is not None:
                            if uninstall_string is not None:
                                if word in uninstall_string: # Uninstall_string here is None
                                        confidence += 5
                        if quiet_uninstall_string is not None:
                            if quiet_uninstall_string is not None:
                                if word in quiet_uninstall_string:
                                    confidence += 5
                        if loc is not None:
                            if word in loc:
                                confidence += 5
                        if url is not None:
                            if word in  url:
                                    confidence += 5
                if final_index is None and final_confidence is None:
                    final_index = index
                    final_confidence = confidence
                if final_confidence < confidence:
                    final_index = index
                    final_confidence = confidence
            index += 1
        return return_array[final_index]


    get_registry_info()
    get_uninstall_string(package_name)
    print('This is the final array: ', final_array)

    if final_array:
        if len(final_array) > 1:
            return get_more_accurate_matches(final_array)
        return final_array
    return_array = []
    for something in total:
        return_array.append(something[0])
    print('This is the return array: ', return_array)
    if len(return_array) > 1:
        return get_more_accurate_matches(return_array)
    else:
        return return_array