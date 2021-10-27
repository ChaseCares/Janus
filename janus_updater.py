import configparser
import subprocess
import argparse
import requests
import logging
import time
import os

from janus_log import setupLogger

PATH_VALETUDO = './Valetudo'
PATH_BINARY = f"{PATH_VALETUDO}/build/armv7/valetudo"
PATH_ROBOTS = './robots'
PATH_LOG = f'./log/janus.log'

GIT_VALETUDO = 'https://github.com/Hypfer/Valetudo'
URL_VALETUDO_VER = 'https://api.github.com/repos/Hypfer/Valetudo/releases/latest'

LOG_NAME = 'janus'


if not os.path.isdir('./identity'):
    os.mkdir('./identity')
if not os.path.isdir('./robots'):
    os.mkdir('./robots')


def parser():
    ap = argparse.ArgumentParser(description='Robot updater helper.')

    ap.add_argument("-u", "--update", required=False, action='store_true',
                    help="Updates the current Valetudo instance.")

    ap.add_argument("-c", "--config", required=False, action='store_true',
                    help="Creates a robot config file.")

    args = ap.parse_args()
    return args


def getVersion(url, site, nothing):
    if site == 'github':
        key = 'tag_name'
    elif site == 'valetudo':
        key = 'release'

    data = requests.get(url).json()

    return list(map(int, data[key].split('.')))


# def getVersion(url, site, update): # For testing
#     if update:
#         if site == 'github':
#             return [2010, 10, 0]
#         elif site == 'valetudo':
#             return [2010, 9, 1]
#     else:
#         if site == 'github':
#             return [2010, 10, 0]
#         elif site == 'valetudo':
#             return [2010, 10, 0]


def checkUpdate(ip):
    robotVer = f'http://{ip}/api/v2/valetudo/version'

    robotVer = getVersion(robotVer, 'valetudo',True)  # Remove True/False
    githubVer = getVersion(URL_VALETUDO_VER, 'github', True)  # Remove True/False

    for i in range(len(githubVer)):
        if robotVer[i] < githubVer[i]:
            return True
    return False


def gitHandler():
    if not os.path.isdir(PATH_VALETUDO):
        subprocess.run([
            'git',
            'clone',
            GIT_VALETUDO,
            ])
    else:
        subprocess.run([
            'cd', PATH_VALETUDO,
            '&&',
            'git', 'restore', '.',
            '&&'
            'git', 'pull',],
            shell=True)


def build():
    try:
        gitHandler()

        subprocess.run([
            'cd', PATH_VALETUDO,
            '&&',
            'npm', 'install',
            '&&',
            'npm', 'run', 'build'],
            shell=True)
    except Exception as e:
        print(e)
        return False
    else:
        return True


def buildCheck(goodUntilTimer=1800):
    log = logging.getLogger(LOG_NAME)
    if os.path.isfile(PATH_BINARY):
        createdTime = os.stat(PATH_BINARY).st_mtime
        if (createdTime + goodUntilTimer) >= time.time():
            log.info(f'Less than {goodUntilTimer/60} minutes old')
            return True
        else:
            log.info(f'Over {goodUntilTimer/60} minutes old')
    return False


def binaryMover(config):
    subprocess.run([
        'scp', '-i',
        config['ROBOT']['identity'],
        '-P', config['ROBOT']['port'],
        PATH_BINARY,
        f"{config['ROBOT']['username']}@{config['ROBOT']['ip']}:/usr/local/bin/"],
        shell=True)


def sshRun(config, command):
    subprocess.run([
        'ssh', '-i',
        config['ROBOT']['identity'],
        '-p', config['ROBOT']['port'],
        f"{config['ROBOT']['username']}@{config['ROBOT']['ip']}",
        *command],
        shell=True, check=True)


def sshHandler(config):
    log = logging.getLogger(LOG_NAME)

    sshRun(config, ['rm', '/usr/local/bin/valetudo'])
    binaryMover(config)
    sshRun(config, ['chmod', '777', '/usr/local/bin/valetudo'])
    sshRun(config, ['/sbin/reboot'])

    log.info('Upload complete, robot should be rebooting.')


def docked(config):
    robotStatus = f"http://{config['ROBOT']['ip']}/api/v2/robot/state/attributes"
    try:
        return requests.get(robotStatus).json()[4]['value'] == 'docked'
    except TypeError:
        return False


def  generateConfig():
    if not os.path.isdir(PATH_ROBOTS):
        os.mkdir(PATH_ROBOTS)

    config = configparser.ConfigParser()

    robotName = input('Name of robot: ')

    if os.path.isfile(f'{PATH_ROBOTS}/{robotName}.ini'):
        raise Exception('Robot config file already exists')

    robotIP = input('IP of robot: ')
    robotPort = input('ssh port of robot: ')
    robotUsername = input('Username of robot: ')
    robotIdentity = input('ssh identity file for robot: ')

    config['ROBOT'] = {
        'name': robotName,
        'ip': robotIP,
        'port': robotPort,
        'username': robotUsername,
        'identity': robotIdentity,
        }
    with open(f'{PATH_ROBOTS}/{robotName}.ini', 'w') as configfile:
        config.write(configfile)


def loadConfig(configFile):
    if configCheck():
        config = configparser.ConfigParser()
        config.read(f'{PATH_ROBOTS}/{configFile}')
        return config
    else:
        raise Exception('No config available')


def configCheck():
    if len(os.listdir(PATH_ROBOTS)) >= 1:
        return True
    return False


def update(config):
    log = logging.getLogger(LOG_NAME)

    if docked(config):
        if checkUpdate(config['ROBOT']['ip']):
            if buildCheck():
                sshHandler(config)
            else:
                build()
                sshHandler(config)
        else:
            log.info(
                f"Skipping {config['ROBOT']['name']} because it's up-to-date")
    else:
        log.info(f"Skipping {config['ROBOT']['name']} because it's not docked")


def main(args):
    log = setupLogger(LOG_NAME, PATH_LOG)

    if (args.config):
        generateConfig()
    elif (args.update):
        for configFile in os.listdir(PATH_ROBOTS):
            config = loadConfig(configFile)
            log.info(config['ROBOT']['name'])
            update(config)
    else:
        log.info('Doing nothing.')

if __name__ == '__main__':
    args = parser()
    main(args)
