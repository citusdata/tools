set -euxo pipefail

while getopts p: flag; do
  case "${flag}" in
  p) PATH=${OPTARG} ;;
  *) ;;
  esac
done

echo "File: ${PATH}"
[ -z "${PATH}" ] && echo "File Path should not be empty Usage ./configure_microsoft_packages.sh -p <file-path>" && exit 1

sudo apt-get install python3-openssl python3-adal jo alien
sudo dpkg -i "${PATH}/azure-repoapi-client_1.0.5-beta_amd64.deb"

mkdir -p ~/.repoclient
# Uses package-repo-service.trafficmanager.net instead of
# package-repo-service.corp.microsoft.com, because that one cano
# only be resolved on corpnet
cat >~/.repoclient/config.json <<EOD
{
"server": "package-repo-service.trafficmanager.net",
"port": "443",
"AADClientId": "fed01f70-081c-4e14-abed-b15a00c1fcac",
"AADClientSecret": "${REPO_CLIENT_SECRET}",
"AADResource": "https://microsoft.onmicrosoft.com/945999e9-da09-4b5b-878f-b66c414602c0",
"AADTenant": "72f988bf-86f1-41af-91ab-2d7cd011db47",
"AADAuthorityUrl": "https://login.microsoftonline.com",
"repositoryId": "something-needs-to-be-here"
}
EOD
#cat ~/.repoclient/config.json
#repoclient repo list | jq '.[] | select(.url | startswith("citus"))'

# Fix a bug in repoclient
sudo sed 's/resp.status_code != 200/resp.status_code >= 300/' -i /usr/lib/python3/dist-packages/azure/repoclient/repolib.py

# Import microsoft key to hide warnings
curl https://packages.microsoft.com/keys/microsoft.asc >microsoft.asc && sudo rpm --import microsoft.asc
