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

__version__ = "1.0.5"


###########################################################################
# HOOK pibooth
###########################################################################

@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the new configuration options"""
    cfg.add_option('NEXTCLOUD', 'activate', True,
                   "Enable upload on Nextcloud",
                   "Enable upload", ['True', 'False'])
    cfg.add_option('NEXTCLOUD', 'rep_photos_nextcloud', "Photos",
                   "Path to photos directory",
                   "rep_photos_nextcloud", "Photos")
    cfg.add_option('NEXTCLOUD', 'album_name', "Pibooth",
                   "Album where pictures are uploaded",
                   "Album name", "Pibooth")
    cfg.add_option('NEXTCLOUD', 'host_nextcloud', '',
                   "URL Nextcloud Server",
                   "NextCloud URL", "https://nextcloud.localhost")
    cfg.add_option('NEXTCLOUD', 'user_nextcloud', 'selfiebox',
                   "Nextcloud User",
                   "User Login NextCloud", "selfiebox")
    cfg.add_option('NEXTCLOUD', 'pass_nextcloud', 'pwd123',
                   "Nextcloud password",
                   "Password NextCloud", "alpammm")
    cfg.add_option('NEXTCLOUD', 'useSynchronize', True,
                   "Use Nextcloudcmd for Synchronize Local et Remote directory",
                   "useSynchronize", ['True', 'False'])
    cfg.add_option('NEXTCLOUD', 'gallery_app', "direct",
                   "Gallery app for QR code URL (direct, photos, or gallery)",
                   "Gallery App", ['direct', 'photos', 'gallery'])
    cfg.add_option('NEXTCLOUD', 'check_quota', True,
                   "Check available disk space before upload",
                   "Check Quota", ['True', 'False'])
    cfg.add_option('NEXTCLOUD', 'min_space_mb', 100,
                   "Minimum free space in MB required for upload",
                   "Min Space (MB)", "100")



@pibooth.hookimpl
def pibooth_startup(app, cfg):

    """Create the NextcloudUpload instance."""

    LOGGER.info("Create the NextcloudUpload Instance")
    app.nextcloud = NextcloudUpload(credentials=None)

    app.nextcloud.nhost = cfg.get('NEXTCLOUD', 'host_nextcloud')
    app.nextcloud.nuser = cfg.get('NEXTCLOUD', 'user_nextcloud')
    app.nextcloud.npassword = cfg.get('NEXTCLOUD', 'pass_nextcloud')
    app.nextcloud.activate_state = cfg.getboolean('NEXTCLOUD', 'activate')
    app.nextcloud.rep_photos_nextcloud = cfg.get('NEXTCLOUD', 'rep_photos_nextcloud')
    app.nextcloud.album_name = cfg.get('NEXTCLOUD', 'album_name')
    app.nextcloud.useSynchronize = cfg.get('NEXTCLOUD', 'useSynchronize')
    app.nextcloud.local_rep = cfg.get('GENERAL', 'directory')
    app.nextcloud.gallery_app = cfg.get('NEXTCLOUD', 'gallery_app')
    app.nextcloud.check_quota = cfg.getboolean('NEXTCLOUD', 'check_quota')
    app.nextcloud.min_space_mb = cfg.getint('NEXTCLOUD', 'min_space_mb')

    # Track connection/quota issues for user feedback
    app.nextcloud.last_error = None

    if not app.nextcloud.wait_for_internet_connection():
        LOGGER.warning("No internet connection available")
        app.nextcloud.is_connected = False
        app.nextcloud.last_error = "Pas de connexion internet"
        app.nextcloud_link_gallery = "Hors ligne"
    else:
        app.nextcloud.oc = app.nextcloud.login(
            app.nextcloud.nhost,
            app.nextcloud.nuser,
            app.nextcloud.npassword
        )

        # Initialize Rep Event on Cloud (Create directory and Share)
        LOGGER.info("Create Directory and Share")

        if app.nextcloud.is_connected:
            # Check disk quota if enabled
            if app.nextcloud.check_quota:
                quota_ok, quota_msg = app.nextcloud.check_disk_quota()
                if not quota_ok:
                    LOGGER.warning("Quota check failed: %s", quota_msg)
                    app.nextcloud.last_error = quota_msg

            LOGGER.info("Create Link (%s)...", app.nextcloud.album_name)
            app.nextcloud_link, error_msg = app.nextcloud.create_share_dir(
                app.nextcloud.rep_photos_nextcloud,
                app.nextcloud.album_name
            )

            if error_msg:
                app.nextcloud.last_error = error_msg

            LOGGER.info("Create Share remote Dir (%s)...", app.nextcloud_link)

            if app.nextcloud_link:
                app.nextcloud_link_gallery = app.nextcloud.create_url_gallery(app.nextcloud_link)
                LOGGER.info("Create Link Gallery (%s)...", app.nextcloud_link_gallery)
            else:
                LOGGER.warning("Could not create share link, using fallback")
                app.nextcloud_link_gallery = "Lien indisponible"
        else:
            app.nextcloud_link_gallery = "Non connecte"

    # Create QrCode image with URL to Gallery on Nextcloud
    LOGGER.info("Create QrCode with URL Link Gallery (%s)...", app.nextcloud_link_gallery)

    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=5,
                       border=2)
    qr.add_data(app.nextcloud_link_gallery)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    image.save(app.nextcloud.local_rep + '/QRCODE.png', "PNG")

    app.nextcloud.qr_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)



@pibooth.hookimpl
def state_wait_enter(cfg, app, win):
    """Actions performed when application enter in Wait state.
    :param cfg: application configuration
    :param app: application instance
    :param win: graphical window instance
    """
    LOGGER.info("In state_wait_enter (%s)", app.previous_picture_file)
    """
    Display the QR Code
    """
    win_rect = win.get_rect()
    qr_rect = app.nextcloud.qr_image.get_rect()
    win.surface.blit(app.nextcloud.qr_image, (10, 10))



@pibooth.hookimpl
def state_processing_exit(app, cfg):
    """Upload picture to Nextcloud album"""
    name = app.previous_picture_file
    rep_photos_nextcloud = app.nextcloud.rep_photos_nextcloud
    nextcloud_name = app.nextcloud.album_name
    activate_state = app.nextcloud.activate_state
    local_rep = app.nextcloud.local_rep

    # Check quota before upload if enabled
    if app.nextcloud.is_connected and app.nextcloud.check_quota:
        quota_ok, quota_msg = app.nextcloud.check_disk_quota()
        if not quota_ok:
            LOGGER.error("Cannot upload: %s", quota_msg)
            app.nextcloud.last_error = quota_msg
            return

    if app.nextcloud.useSynchronize == 'True' or app.nextcloud.useSynchronize == True:
        LOGGER.info("Synchronize Directory local to Remote (%s)...", name)
        app.nextcloud.synchronize_pics(local_rep, rep_photos_nextcloud, nextcloud_name)
    else:
        LOGGER.info("Upload Photo (%s)...", name)
        app.nextcloud.upload_photos(
            name,
            app.nextcloud.rep_photos_nextcloud + nextcloud_name + '/' + os.path.basename(name),
            activate_state
        )


###########################################################################
# Class
###########################################################################

class NextcloudUpload(object):

    app = None

    def __init__(self, credentials=None, activate=True):
        """Initialize NextcloudUpload instance
        :param credentials: file create at first run to keep allow API use
        :type credentials: file
        :param activate: use to disable the plugin
        :type activate: bool
        """
        self.is_connected = False
        self.last_error = None
        self.gallery_app = "photos"
        self.check_quota = True
        self.min_space_mb = 100

    def _is_internet(self):
        """check internet connexion"""
        try:
            requests.get('https://www.google.com/', timeout=5).status_code
            return True
        except (requests.ConnectionError, requests.Timeout):
            LOGGER.warning("No internet connection!!!!")
            return False

    def wait_for_internet_connection(self):
        req = Request("http://google.com/")
        for timeout in [1, 5, 10, 15]:
            try:
                response = urlopen(req, timeout=timeout)
                return True
            except URLError as err:
                pass
        return False

    def login(self, nhost, nuser, npassword):
        """Perform actions when state is activated
        """
        self.nhost = nhost
        self.nuser = nuser
        self.npassword = npassword

        LOGGER.info("Login Host (%s)...", self.nhost)
        LOGGER.info("Login User (%s)...", self.nuser)

        oc = owncloud.Client(nhost, single_session=True)

        try:
            oc.login(nuser, npassword)
            self.is_connected = True
            self.oc = oc
            LOGGER.info("Nextcloud Login OK !! (%s)", nhost)
        except owncloud.HTTPResponseError as e:
            self.is_connected = False
            if e.status_code == 401:
                self.last_error = "Identifiants incorrects"
                LOGGER.error("Nextcloud authentication failed: invalid credentials")
            else:
                self.last_error = f"Erreur HTTP {e.status_code}"
                LOGGER.error("Nextcloud HTTP error: %s", e.status_code)
        except Exception as e:
            self.is_connected = False
            self.last_error = "Connexion impossible"
            LOGGER.warning("Nextcloud Not Connected !! (%s) - %s", nhost, str(e))

        return oc if self.is_connected else None

    def check_disk_quota(self):
        """Check available disk space on Nextcloud
        Returns: (bool, str) - (is_ok, message)
        """
        if not self.is_connected:
            return False, "Non connecte"

        try:
            # Get user quota information
            user_info = self.oc.get_attribute('quota')

            if user_info is None:
                # Try alternative method using WebDAV
                return self._check_quota_webdav()

            free_bytes = user_info.get('free', 0)
            free_mb = free_bytes / (1024 * 1024)

            if free_mb < self.min_space_mb:
                return False, f"Espace insuffisant: {free_mb:.0f}MB libre (min: {self.min_space_mb}MB)"

            LOGGER.info("Disk quota OK: %.0f MB free", free_mb)
            return True, f"{free_mb:.0f}MB libre"

        except Exception as e:
            LOGGER.warning("Could not check quota: %s", str(e))
            # Don't block if we can't check quota
            return True, "Quota non verifie"

    def _check_quota_webdav(self):
        """Alternative quota check using WebDAV PROPFIND"""
        try:
            import xml.etree.ElementTree as ET

            url = f"{self.nhost}/remote.php/dav/files/{self.nuser}/"
            headers = {'Depth': '0'}
            body = '''<?xml version="1.0"?>
            <d:propfind xmlns:d="DAV:">
                <d:prop>
                    <d:quota-available-bytes/>
                    <d:quota-used-bytes/>
                </d:prop>
            </d:propfind>'''

            response = requests.request(
                'PROPFIND',
                url,
                auth=(self.nuser, self.npassword),
                headers=headers,
                data=body,
                timeout=10
            )

            if response.status_code == 207:
                # Parse XML response
                root = ET.fromstring(response.content)
                ns = {'d': 'DAV:'}

                available = root.find('.//d:quota-available-bytes', ns)
                used = root.find('.//d:quota-used-bytes', ns)

                if available is not None and available.text:
                    free_bytes = int(available.text)
                    if free_bytes < 0:  # -3 means unlimited
                        return True, "Quota illimite"

                    free_mb = free_bytes / (1024 * 1024)

                    if free_mb < self.min_space_mb:
                        return False, f"Disque plein: {free_mb:.0f}MB libre"

                    LOGGER.info("Disk quota OK (WebDAV): %.0f MB free", free_mb)
                    return True, f"{free_mb:.0f}MB libre"

            return True, "Quota non verifie"

        except Exception as e:
            LOGGER.warning("WebDAV quota check failed: %s", str(e))
            return True, "Quota non verifie"

    def create_share_dir(self, rep_photos_nextcloud, album_name):
        """Create directory to Cloud and Share
        Returns: (link, error_message)
        """
        if not rep_photos_nextcloud[-1] == '/':
            rep_photos_nextcloud += '/'
        if not rep_photos_nextcloud[0] == '/':
            rep_photos_nextcloud = '/' + rep_photos_nextcloud

        self.rep_photos_nextcloud = rep_photos_nextcloud
        error_msg = None

        # Create base directory
        try:
            self.oc.mkdir(self.rep_photos_nextcloud)
            LOGGER.info("Successfully created rep_photos_nextcloud !! (%s)", self.rep_photos_nextcloud)
        except owncloud.HTTPResponseError as e:
            if e.status_code == 405:
                LOGGER.info("rep_photos_nextcloud already exists (%s)", self.rep_photos_nextcloud)
            elif e.status_code == 507:
                error_msg = "Disque plein sur le serveur"
                LOGGER.error("Disk full on Nextcloud server!")
                return "", error_msg
            else:
                LOGGER.info("rep_photos_nextcloud creation returned %s", e.status_code)
        except Exception as e:
            LOGGER.info("rep_photos_nextcloud Already exist !! (%s)", self.rep_photos_nextcloud)

        # Create Album directory
        try:
            self.oc.mkdir(self.rep_photos_nextcloud + album_name)
            LOGGER.info("Successfully created the directory (%s)", self.rep_photos_nextcloud + album_name)
        except owncloud.HTTPResponseError as e:
            if e.status_code == 405:
                LOGGER.info("Directory already exists (%s)", self.rep_photos_nextcloud + album_name)
            elif e.status_code == 403:
                error_msg = "Permission refusee ou disque plein"
                LOGGER.warning("Permission denied or disk full for directory creation")
            elif e.status_code == 507:
                error_msg = "Disque plein sur le serveur"
                LOGGER.error("Disk full on Nextcloud server!")
                return "", error_msg
            else:
                LOGGER.info("Directory creation returned %s", e.status_code)
        except Exception as e:
            LOGGER.info("Creation of the directory (%s) failed: %s", self.rep_photos_nextcloud + album_name, str(e))

        LOGGER.info("Nextcloud Create Share Link (%s)", self.rep_photos_nextcloud + album_name)

        # Check if share already exists
        try:
            existing_shares = self.oc.get_shares(self.rep_photos_nextcloud + album_name)
            if existing_shares:
                LOGGER.info("Share Link Already Exists (%s)", self.rep_photos_nextcloud + album_name)
                return existing_shares[0].get_link(), error_msg
        except Exception as e:
            LOGGER.info("No existing share found, creating new one")

        # Create new share link
        try:
            link_info = self.oc.share_file_with_link(self.rep_photos_nextcloud + album_name, public_upload=False)
            return link_info.get_link(), error_msg
        except owncloud.HTTPResponseError as e:
            if e.status_code == 404:
                error_msg = "Dossier introuvable - verifier les permissions"
                LOGGER.error("Failed to create share: folder not found (404)")
            elif e.status_code == 403:
                error_msg = "Permission refusee pour le partage"
                LOGGER.error("Failed to create share: permission denied (403)")
            else:
                error_msg = f"Erreur partage: {e.status_code}"
                LOGGER.error("Failed to create share link: HTTP %s", e.status_code)
            return "", error_msg
        except Exception as e:
            error_msg = f"Erreur: {str(e)}"
            LOGGER.error("Failed to create share link: %s", str(e))
            return "", error_msg


    def create_url_gallery(self, link):
        """Create URL for Gallery/Photos app based on configuration

        URL formats:
        - direct: https://nextcloud.domain/s/shareToken (default, most reliable)
        - photos: https://nextcloud.domain/apps/photos/public/shareToken
        - gallery: https://nextcloud.domain/apps/gallery/s/shareToken (legacy)
        """
        if not link:
            return link

        # Extract share token from link (e.g., /s/pHPtiFffE3FbnpM -> pHPtiFffE3FbnpM)
        import re
        match = re.search(r'/s/([a-zA-Z0-9]+)', link)
        if not match:
            LOGGER.warning("Could not extract share token from link: %s", link)
            return link

        share_token = match.group(1)

        if self.gallery_app == "photos":
            # Nextcloud Photos app public view
            return f"{self.nhost}/apps/photos/public/{share_token}"
        elif self.gallery_app == "gallery":
            # Legacy Gallery app
            return f"{self.nhost}/apps/gallery/s/{share_token}"
        else:  # default to "direct"
            # Direct share link (most reliable)
            return link

    def upload_photos(self, local_source_file, album_name, activate):
        """Upload photo to Nextcloud
        :param local_source_file: Path to local file to upload
        :type local_source_file: str
        :param album_name: name of album to upload to
        :type album_name: str
        :param activate: use to disable the upload
        :type activate: bool
        """
        self.activate = activate

        # Check if connected
        if not self.is_connected:
            LOGGER.error("Cannot upload: not connected to Nextcloud")
            self.last_error = "Non connecte"
            return False

        # Check internet connection
        if not self._is_internet():
            LOGGER.error("Interrupt upload: no internet connection")
            self.last_error = "Pas de connexion internet"
            return False

        # Check if plugin is disabled
        if not self.activate:
            LOGGER.info("Upload disabled in configuration")
            return False

        LOGGER.info("In upload_photos Local (%s)", local_source_file)
        LOGGER.info("In upload_photos Remote (%s)", album_name)

        try:
            self.oc.put_file(album_name, local_source_file)
            LOGGER.info("Photo uploaded to Nextcloud successfully!")
            self.last_error = None
            return True
        except owncloud.HTTPResponseError as e:
            if e.status_code == 507:
                self.last_error = "Disque plein"
                LOGGER.error("Upload failed: disk full on server (507)")
            elif e.status_code == 403:
                self.last_error = "Permission refusee"
                LOGGER.error("Upload failed: permission denied (403)")
            elif e.status_code == 404:
                self.last_error = "Dossier introuvable"
                LOGGER.error("Upload failed: destination folder not found (404)")
            else:
                self.last_error = f"Erreur HTTP {e.status_code}"
                LOGGER.error("Upload failed: HTTP error %s", e.status_code)
            return False
        except Exception as e:
            self.last_error = "Erreur upload"
            LOGGER.error("Error while uploading file to Nextcloud: %s", str(e))
            return False


    def synchronize_pics(self, local_rep, rep_photos_nextcloud, album_name):
        """Synchronize local directory with Nextcloud using nextcloudcmd
        """
        if not self.is_connected:
            LOGGER.warning("Synchronize: not connected to Nextcloud")
            return False

        # Build nextcloudcmd command
        USER_NC = self.nuser
        PASS_NC = self.npassword
        LOCAL_PATH_NC = local_rep
        REMOTE_PATH_NC = self.nhost + "/remote.php/webdav/" + rep_photos_nextcloud + "/" + album_name

        nextcloudcmd = (
            f"nextcloudcmd -u {USER_NC} -p {PASS_NC} "
            f"--path {rep_photos_nextcloud}{album_name} "
            f"-s {LOCAL_PATH_NC} {REMOTE_PATH_NC}"
        )

        LOGGER.info("Running nextcloudcmd synchronization...")
        result = os.system(nextcloudcmd)

        if result != 0:
            LOGGER.warning("nextcloudcmd returned non-zero exit code: %s", result)
            self.last_error = "Erreur synchronisation"
            return False

        LOGGER.info("Synchronization completed successfully")
        return True
