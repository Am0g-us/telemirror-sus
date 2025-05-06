from typing import Tuple, Type
from telethon import TelegramClient
from telethon.tl import types
from telethon.tl.types import InputFile
from ..hints import EventMessage, EventLike
from .base import MessageFilter

class RestrictSavingContentBypassFilter(MessageFilter):
    """Filter that bypasses saving content restriction by re-uploading media"""

    @property
    def restricted_content_allowed(self) -> bool:
        return True

    def _get_file_name(self, media, default_name: str) -> str:
        """Extract file name with correct extension from media."""
        if isinstance(media, types.MessageMediaDocument):
            for attr in media.document.attributes:
                if isinstance(attr, types.DocumentAttributeFilename):
                    return attr.file_name
            mime = media.document.mime_type
            # Map common MIME types to extensions
            mime_to_ext = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'video/mp4': '.mp4',
                'video/mpeg': '.mpeg',
                'audio/mpeg': '.mp3',
                'audio/ogg': '.ogg',
                'application/pdf': '.pdf'
            }
            return default_name + mime_to_ext.get(mime, '.bin')
        return default_name

    async def _process_message(
        self, message: EventMessage, event_type: Type[EventLike]
    ) -> Tuple[bool, EventMessage]:

        if message.media is None or (
            message.chat is None or not message.chat.noforwards
        ):
            return True, message

        client: TelegramClient = message.client

        # Handle different media types
        if isinstance(message.media, types.MessageMediaPhoto):
            # Handle photos
            photo: bytes = await client.download_media(message=message, file=bytes)
            file_name = self._get_file_name(message.media, 'photo.jpg')
            cloned_photo: InputFile = await client.upload_file(file=photo, file_name=file_name)
            message.media = cloned_photo

        elif isinstance(message.media, types.MessageMediaDocument):
            # Handle documents (videos, files, GIFs, etc.)
            document: bytes = await client.download_media(message=message, file=bytes)
            file_name = self._get_file_name(message.media, 'document')
            cloned_document: InputFile = await client.upload_file(file=document, file_name=file_name)
            message.media = cloned_document

        elif isinstance(message.media, types.MessageMediaWebPage):
            # Keep webpages as is
            pass

        elif isinstance(message.media, types.MessageMediaGeo):
            # Keep location data
            message.media = types.MessageMediaGeo(
                geo=message.media.geo,
                ttl_seconds=message.media.ttl_seconds
            )

        else:
            # Remove unsupported media types
            message.media = None

        # Process message if not empty
        return bool(message.media or message.message), message
