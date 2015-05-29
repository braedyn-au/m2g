#!/usr/bin/env python

# Copyright 2014 Open Connectome Project (http://openconnecto.me)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# raw_upload.py
# Created by Disa Mhembere on 2015-05-28.
# Email: disa@jhu.edu

import argparse
import os
from time import strftime, localtime
import threading

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import get_script_prefix
from django.conf import settings

from ocpipeline.forms import RawUploadForm
from ocpipeline.models import RawUploadModel
from ocpipeline.utils.util import saveFileToDisk, sendEmail
from ocpipeline.procs.runc4 import runc4

def raw_upload(request):

  if request.method == "POST":
    form = RawUploadForm(request.POST, request.FILES) # instantiating form
    if form.is_valid():
      # TODO: Alter save path
      data_dir = os.path.join(settings.MEDIA_ROOT, 'tmp', strftime("rawUpload%a%d%b%Y_%H.%M.%S/", localtime()))

      nifti_paths = [] # paths the nifti images
      b_paths = [] # paths to b vals and vects

      # Save niftis
      for _file in form.cleaned_data["niftis"]:
        nifti_paths.append(os.path.join(data_dir, _file.name))
        saveFileToDisk(_file, nifti_paths[len(nifti_paths)-1])
      # Save b's
      for _file in form.cleaned_data["bs"]:
        saveFileToDisk(_file, os.path.join(data_dir, _file.name))

      ru_model = RawUploadModel()
      ru_model.mpragepath = nifti_paths[0] if len(nifti_paths) > 0 else ""
      ru_model.dtipath = nifti_paths[1] if len(nifti_paths) > 0 else ""
      ru_model.fmripath = nifti_paths[2] if len(nifti_paths) > 0 else ""
      ru_model.atlas = form.cleaned_data["atlas"]
      ru_model.graphsize = "big" if form.cleaned_data["graphsize"] == True else "small"
      ru_model.email = form.cleaned_data["email"] 
      ru_model.save() # Sync to Db

      thr = threading.Thread(target=runc4, args=(nifti_paths, b_paths, 
            (form.cleaned_data["graphsize"], form.cleaned_data["atlas"]), 
            form.cleaned_data["email"],))
      thr.start()

      """
      runc4(nifti_paths, b_paths, opts=(form.cleaned_data["graphsize"], \
                  form.cleaned_data["atlas"]), email=form.cleaned_data["email"])
      """


      sendEmail(form.cleaned_data["email"], "MR Images to graphs job started", 
              "Hello,\n\nYour job launched successfully. You will receive another email upon completion.\n\n")


      request.session["success_msg"] =\
"""
Your job successfully launched. You should receive an email to confirm launch
and another when it upon job completion. <br/>
<i>The process may take several hours</i> if you selected to compute all invariants.
"""
      return HttpResponseRedirect(get_script_prefix()+"success")

  else:
    form = RawUploadForm() # An empty, unbound form

  return render_to_response(
    "c4.html",
    {"RawUploadForm": form},
    context_instance=RequestContext(request)
    )
