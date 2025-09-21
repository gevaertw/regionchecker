#!/bin/bash
#loading vars and login to Azure
source loadvar.sh
source azCliAuthenticate.sh

echo "ℹ️  Creating Resource group ${RGName} in location ${deploymentLocation}"
az group create \
    --name "${RGName}" \
    --location "${deploymentLocation}"

echo "ℹ️  Creating Storage Account ${storageAccountName} in resource group ${RGName}"
az storage account create \
    --name "${storageAccountName}" \
    --resource-group "${RGName}" \
    --location "${deploymentLocation}" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --allow-blob-public-access true

echo "ℹ️  Enabling static website hosting on storage account ${storageAccountName}"
az storage blob service-properties update \
    --account-name ${storageAccountName} \
    --static-website \
    --index-document "index.html" \
    --404-document "404.html"

echo "ℹ️  Creating managed identity ${managedidentityName} in resource group ${RGName}"
az identity create \
    --name "${managedidentityName}" \
    --resource-group "${RGName}"

echo "ℹ️  Assigning 'Storage Blob Data Contributor' role to managed identity ${managedidentityName} for storage account ${storageAccountName}"
az role assignment create \
    --assignee $(az identity show --name "${managedidentityName}" --resource-group "${RGName}" --query principalId -o tsv) \
    --role "Storage Blob Data Contributor" \
    --scope $(az storage account show --name "${storageAccountName}" --resource-group "${RGName}" --query id -o tsv)





