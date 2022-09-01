import logging
import subprocess
import win32com.shell.shell as shell

proxy_server_query = 'reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer'
proxy_status_query = 'reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable'
deactivate_proxy = 'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f'
activate_proxy = 'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f'


logger = logging.getLogger(__name__)


def activate():
    # check current regkey value for proxy
    shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe',
                         lpParameters='/c ' + activate_proxy)
    logger.info('activated Proxy')


def deactivate():
    shell.ShellExecuteEx(lpVerb='runas', lpFile='cmd.exe',
                         lpParameters='/c ' + deactivate_proxy)
    logger.info('deactivated Proxy')


def change_address(new_address):
    shell.ShellExecuteEx(lpFile='cmd.exe',
                         lpParameters='/c ' + f'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /t REG_SZ /d {new_address} /f')
    logger.info(f"Changed Proxy Server to {new_address}")


def fill_in():
    try:
        value = subprocess.check_output(
            proxy_server_query).decode("utf-8").split()[-1]
        return value
    except:
        value = "0.0.0.0:0"
        return value


def status_check():
    global logger
    # check current regkey value for proxy
    regkey_check = subprocess.Popen(
        proxy_status_query, shell=True, stdout=subprocess.PIPE)
    regkey_check_return = regkey_check.stdout.read().split()

    if regkey_check_return[-1] == b'0x0':
        logger.info('Proxy is currently inactive')
        return
    if regkey_check_return[-1] == b'0x1':
        logger.info('Proxy is currently active')
        return
    else:
        logger.debug(
            f"{regkey_check_return[-1]}, {type(regkey_check_return[-1])}")


def server_check():
    global logger
    # check current regkey value for proxy
    regkey_check = subprocess.Popen(
        proxy_server_query, shell=True, stdout=subprocess.PIPE)
    regkey_check_return = regkey_check.stdout.read().split()

    # try to convert outputted bytes to string
    try:
        value = regkey_check_return[-1].decode("utf-8")
        # if output was indeed bytes return its value which now should be a string to main.py
        if type(regkey_check_return[-1]) is bytes:
            logger.info(f"Current Proxy Server: {value}")
            return value
        else:
            # if the output was not in bytes log its value and type for debugging purposes
            logger.debug(
                f"{regkey_check_return[-1]}, {type(regkey_check_return[-1])}")

    # handle error most likely resulting from missing reg key
    except:
        # create missing reg key with placeholder address
        logger.warning("No Proxy Server found!")
        logger.info("Creating REG_SZ key, setting proxy address...")
        create_proxy_regsz = subprocess.Popen(
            f'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /t REG_SZ /d 0.0.0.0:0 /f', shell=True, stdout=subprocess.PIPE)
        create_proxy_regsz_return = create_proxy_regsz.stdout.read()
        create_proxy_regsz_return = create_proxy_regsz_return.decode(
            "utf-8").split()
        logger.info(" ".join(create_proxy_regsz_return))
        logger.info("Set Proxy address to: 0.0.0.0:0")

        # try to read the value again
        regkey_check2 = subprocess.Popen(
            proxy_server_query, shell=True, stdout=subprocess.PIPE)
        regkey_check_return2 = regkey_check2.stdout.read().split()

        # convert outputted bytes to string
        value = regkey_check_return2[-1].decode("utf-8")
        if type(regkey_check_return2[-1]) is bytes:
            logger.info(f"Current Proxy Server: {value}")
            return value
        else:
            logger.debug(
                f"{regkey_check_return2[-1]}, {type(regkey_check_return2[-1])}")
