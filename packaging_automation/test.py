import re
test=r".*Citus 10.2.1 on x86_64-(pc|unknown)-linux-gnu, compiled by gcc.*"
param2 ='                                              citus_version                                               \n----------------------------------------------------------------------------------------------------------\n Citus 10.2.1 on x86_64-unknown-linux-gnu, compiled by gcc (GCC) 8.3.1 20190311 (Red Hat 8.3.1-3), 64-bit\n(1 row)\n\n'
if re.match(test, repr(param2)):
    print(True)
else:
    print(False)


# test=  r"^'waiting for server to start.... done\\nserver started\\n'$"
# param='waiting for server to start.... done\nserver started\n'
#
# print(repr(param))
# print(param)
# if re.match(test, repr(param)):
#     print(True)
# else:
#     print(False)