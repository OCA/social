Creating a new preview file
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to add the configuration in three places:

* Function `_checkAttachment` and `_hasPreview` from `mail.DocumentViewer` on
  Javascript
* Qweb template `DocumentViewer.Content`

To use this module, you need to:

#. Go to Settings > Technical > Attachments
#. Create attachment with image or pdf format
#. Show preview icon in "File content"

As an example, you can check `mail_preview_audio`.
