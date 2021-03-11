#!/bin/bash

 for FILE in $(find ./pkgs/releases -type f );do
   file_name="${FILE##*/}"
   path="${FILE%/*}"
   test_file_name="test_${file_name}"
   echo "Processing renaming on file ${path}/${test_file_name}"
   mv  "${FILE}" "${path}/${test_file_name}"
 done

