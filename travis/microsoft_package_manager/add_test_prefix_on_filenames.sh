#!/bin/bash

 for FILE in ./pkgs/releases/*;do
   file_name="${FILE##*/}"
   path="${FILE%/*}"
   test_file_name="test_${file_name}"
   echo "Processing reniaming on file ${path}/${test_file_name}"
   mv  "${FILE}" "${path}/${test_file_name}"
 done
