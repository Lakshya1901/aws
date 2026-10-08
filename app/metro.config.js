// Lets Metro resolve the shared copy files in ../config/copy (the i18n source of truth).
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
config.watchFolders = [...(config.watchFolders ?? []), path.resolve(__dirname, '../config/copy')];

module.exports = config;
