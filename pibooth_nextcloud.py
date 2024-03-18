# -*- coding: utf-8 -*-

"""Pibooth plugin for Nextcloud upload."""

import json
import os.path

import requests

import os
import traceback
import owncloud
import qrcode
import pygame
from PIL import Image, ImageDraw, ImageFont

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import pibooth

from pibooth.utils import LOGGER

__version__ = "1.0.1"

SECTION = 'NEXTCLOUD'

###########################################################################
# HOOK pibooth
###########################################################################

@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the new configuration options"""
    cfg.add_option(SECTION, 'activate', True,
                   "Enable upload on Nextcloud",
                   "Enable upload", ['True', 'False'])
    cfg.add_option(SECTION, 'rep_photos_nextcloud', "Photos",
                   "Path to photos directory",
                   "rep_photos_nextcloud", "Photos")
    cfg.add_option(SECTION, 'album_name', "Pibooth",
                   "Album where pictures are uploaded",
                   "Album name", "Pibooth")
    cfg.add_option(SECTION, 'host_nextcloud', '',
                   "URL Nextcloud Server",
		   "NextCloud URL", "https://nextcloud.localhost")	
    cfg.add_option(SECTION, 'user_nextcloud', 'selfiebox',
                   "Nextcloud User",
		   "User Login NextCloud", "selfiebox")	
    cfg.add_option(SECTION, 'pass_nextcloud', 'pwd123',
                   "Nextcloud password",
		   "Password NextCloud", "alpammm")
    cfg.add_option(SECTION, 'useSynchronize', True,
                   "Use Nextcloudcmd for Synchronize Local et Remote directory",
		   "useSynchronize", ['True', 'False'])
    cfg.add_option(SECTION, 'printQrCode', True,
                   "Print QR Code on screen",
		   "printQrCode", ['True', 'False'])

				   

@pibooth.hookimpl
def pibooth_startup(app, cfg):

    """Create the NextcloudUpload instance."""

    LOGGER.info("Create the NextcloudUpload Instance")
    app.nextcloud = NextcloudUpload( credentials=None)

    app.nextcloud.nhost = cfg.get(SECTION, 'host_nextcloud')
    app.nextcloud.nuser = cfg.get(SECTION, 'user_nextcloud')
    app.nextcloud.npassword = cfg.get(SECTION, 'pass_nextcloud')
    app.nextcloud.activate_state = cfg.getboolean(SECTION, 'activate')
    app.nextcloud.rep_photos_nextcloud = cfg.get(SECTION, 'rep_photos_nextcloud')
    app.nextcloud.album_name = cfg.get(SECTION, 'album_name')
    app.nextcloud.useSynchronize = cfg.getboolean(SECTION, 'useSynchronize')
    app.nextcloud.printQrCode = cfg.getboolean(SECTION, 'printQrCode')
    app.nextcloud.local_rep = cfg.get('GENERAL', 'directory')

    LOGGER.info("Synchronize is (%r)...",app.nextcloud.useSynchronize)

    app.nextcloud.wait_for_internet_connection()
    app.nextcloud.oc = app.nextcloud.login( app.nextcloud.nhost,
                       app.nextcloud.nuser,
                       app.nextcloud.npassword)

    # Initialize Rep Event on Cloud (Create directory and Share)
    LOGGER.info("Create Directory and Share")

    if app.nextcloud.is_connected:
        LOGGER.info("Create Directory and Album (%s)...",app.nextcloud.album_name)
        app.nextcloud.create_dir(app.nextcloud.rep_photos_nextcloud , app.nextcloud.album_name)

        LOGGER.info("Create Share Link...")
        app.nextcloud_link = app.nextcloud.create_share_link(app.nextcloud.rep_photos_nextcloud , app.nextcloud.album_name)
        LOGGER.info("Share remote Link Public (%s)...",app.nextcloud_link)

        app.nextcloud_link_gallery = app.nextcloud.create_url_gallery(app.nextcloud_link)
        LOGGER.info("Create Link Gallery (%s)...",app.nextcloud_link_gallery)
    else:
        app.nextcloud_link_gallery="Not connected"


    # Create QrCode image with URL to Gallery on Nextcloud
    LOGGER.info("Create QrCode with URL Link Gallery (%s)...",app.nextcloud_link)

    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=5,
                       border=2)
    qr.add_data(app.nextcloud_link)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    image.save(app.nextcloud.local_rep + '/QRCODE.png' ,"PNG")

    app.nextcloud.qr_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)

									
									
@pibooth.hookimpl
def state_wait_enter(cfg, app, win):
    """Actions performed when application enter in Wait state.
    :param cfg: application configuration
    :param app: application instance
    :param win: graphical window instance
    """
    LOGGER.info("In state_wait_enter (%s)",app.previous_picture_file)
    """
    Display the QR Code 
    """
    if app.nextcloud.printQrCode:
        win_rect = win.get_rect()
        qr_rect = app.nextcloud.qr_image.get_rect()
        #win.surface.blit(app.nextcloud.qr_image, (win_rect.width - qr_rect.width - 10,
        #                                   win_rect.height - qr_rect.height - 90))
        win.surface.blit(app.nextcloud.qr_image,(10, 10))



@pibooth.hookimpl
def state_processing_exit(app, cfg):
    """Upload picture to Nextcloud album"""
    name = app.previous_picture_file
    rep_photos_nextcloud = app.nextcloud.rep_photos_nextcloud
    nextcloud_name = app.nextcloud.album_name
    activate_state = app.nextcloud.activate_state
    local_rep = app.nextcloud.local_rep
    
    if app.nextcloud.useSynchronize:
            LOGGER.info("Synchronize Directory local to Remote  (%s)...",name)
            app.nextcloud.synchronize_pics(local_rep, rep_photos_nextcloud, nextcloud_name)
    else:
            LOGGER.info("Upload Photo  (%s)...",name)
            app.nextcloud.upload_photos(name, app.nextcloud.rep_photos_nextcloud +  nextcloud_name + '/' + os.path.basename(name), activate_state)


###########################################################################
# Class
###########################################################################

class NextcloudUpload(object):

    app = None

    def __init__(self,  credentials=None, activate=True):
        """Initialize GoogleUpload instance
        :param credentials: file create at first run to keep allow API use
        :type credentials: file
        :param activate: use to disable the plugin
        :type activate: bool
        """
    def _is_internet(self):
        """check internet connexion"""
        try:
            requests.get('https://www.google.com/').status_code
            return True
        except requests.ConnectionError:
            LOGGER.warning("No internet connection!!!!")
            return False

    def wait_for_internet_connection(self):
        req = Request("http://google.com/")
        for timeout in [1,5,10,15]:
            try:
                response = urlopen(req,timeout=timeout)
                return True
            except URLError as err: pass
            return False

    def login(self, nhost, nuser, npassword):
        """Perform actions when state is activated
        """
        self.nhost = nhost
        self.nuser = nuser
        self.npassword = npassword

        LOGGER.info("Login Host (%s)...",self.nhost)
        LOGGER.info("Login User (%s)...",self.nuser)
#        LOGGER.info("Login Password (%s)...",self.npassword)


        oc = owncloud.Client(nhost, single_session = True)

        try:
            oc.login(nuser, npassword)
            self.is_connected = True
            LOGGER.info("Nextcloud Login OK !! (%s)", nhost)
        except:
            self.is_connected = False
            LOGGER.warning("Nextcloud Not Connected !! (%s)", nhost)

        return oc

    def create_dir(self, rep_photos_nextcloud, album_name):
        """Create directory to Cloud
        """
        if not rep_photos_nextcloud[-1] == '/':
            rep_photos_nextcloud += '/'
        if not rep_photos_nextcloud[0] == '/':
            rep_photos_nextcloud = '/' + rep_photos_nextcloud

        self.rep_photos_nextcloud = rep_photos_nextcloud

        try:
            self.oc.mkdir(self.rep_photos_nextcloud)
        except:
            LOGGER.info("rep_photos_nextcloud Already exist !! (%s)", self.rep_photos_nextcloud)
        else:
            LOGGER.info("Successfully created rep_photos_nextcloud !! (%s)", self.rep_photos_nextcloud)

        """ Create Album Name"""
        try:
            self.oc.mkdir(self.rep_photos_nextcloud + album_name)
        except:
            LOGGER.info("Creation of the directory (%s) failed , may be already exist !! ", self.rep_photos_nextcloud + album_name)
        else:
            LOGGER.info("Successfully created the directory (%s) ", self.rep_photos_nextcloud + album_name)



    def create_share_link(self, rep_photos_nextcloud, album_name):

        LOGGER.info("Nextcloud Create Share Link   (%s)", self.rep_photos_nextcloud + album_name)

        try:
            FileShare=self.oc.get_shares(self.rep_photos_nextcloud + album_name)
        except:
            LOGGER.warning("Problem to get_shares info for  (%s)", self.rep_photos_nextcloud + album_name)

        if not FileShare:
           LOGGER.info("No Share Link ")
           try:
               link_info = self.oc.share_file_with_link(self.rep_photos_nextcloud + album_name, public_upload=False )
           except:
               LOGGER.warning("Problem to create Share Link for  (%s)", self.rep_photos_nextcloud + album_name)
               link=""
           else:
               link=link_info.get_link()
        else:
           LOGGER.info("Share Link Already Exist (%s) ",self.rep_photos_nextcloud + album_name)
           """" possibility to have multiple Share link
           """
           for x in range(len(FileShare)):
               link=FileShare[x].get_link()
        return link


    def create_url_gallery(self, link):
        """Create URL for Gallery
        """
        return link.replace(self.nhost, self.nhost + "/apps/gallery")
		
    def upload_photos(self, local_source_file, album_name, activate):
        """Funtion use to upload list of photos to google album
        :param local_source_file: PAth absolue to loca file to upload
        :type local_source_file: str
        :param album_name: name of albums to upload
        :type album_name: str
        :param activate: use to disable the upload
        :type activate: bool
        """
        self.activate = activate
        # interrupt upload no internet
        if not self._is_internet():
            LOGGER.error("Interrupt upload no internet connexion!!!!")
            return
        # if plugin is disable
        if not self.activate:
            LOGGER.error("Interrupt upload no activated !!!! (%s)",str(self.activate))
            return

        LOGGER.info("In upload_photos Local  (%s)", local_source_file)
        LOGGER.info("In upload_photos Remote  (%s)", album_name)
        if not self.oc.put_file(album_name, local_source_file):
            LOGGER.error("Error while upload file to Nextcloud !!!!")
            return
        else:
            LOGGER.info("Photo upload to Nextcloud !!!!")
	    

    def synchronize_pics(self, local_rep, rep_photos_nextcloud, album_name):
        """ Upload Photos to Nextcloud
        """
        if not self.is_connected:
            LOGGER.warning("Synchronize No internet connection")
        else:
            #Syncho repertoire nextcloud / upload
            USER_NC= self.nuser
            PASS_NC = self.npassword
            LOCAL_PATH_NC= local_rep
            REMOTE_PATH_NC=self.nhost + "/remote.php/webdav" + rep_photos_nextcloud + album_name
            nextcloudcmd = "nextcloudcmd" + " -u " + USER_NC + " -p " + PASS_NC + " -s  " + LOCAL_PATH_NC + " " + REMOTE_PATH_NC
            LOGGER.info("Os Command   (%s)", nextcloudcmd)
            os.system(nextcloudcmd)


