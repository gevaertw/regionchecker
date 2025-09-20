#!/bin/bash
#loading vars and login to Azure
source loadvar.sh
source azCliAuthenticate.sh

az group create \
    --name "${RGName}" \
    --location "${deploymentLocation}"

az storage account create \
    --name "${storageAccountName}" \
    --resource-group "${RGName}" \
    --location "${deploymentLocation}" \
    --sku Standard_LRS \
    --kind StorageV2

az storage blob service-properties update \
    --account-name "${storageAccountName}" \
    --resource-group "${RGName}" \
    --static-website \
    --404-document 404.html \
    --index-document index.html

az identity create \
    --name "${managedidentityName}" \
    --resource-group "${RGName}"

az role assignment create \
    --assignee $(az identity show --name "${managedidentityName}" --resource-group "${RGName}" --query principalId -o tsv) \
    --role "Storage Blob Data Contributor" \
    --scope $(az storage account show --name "${storageAccountName}" --resource-group "${RGName}" --query id -o tsv)





