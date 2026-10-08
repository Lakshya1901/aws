// Lets Metro resolve the shared config: copy files in ../config/copy (the i18n source of truth) and model.json.
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
config.watchFolders = [...(config.watchFolders ?? []), path.resolve(__dirname, '../config')];

module.exports = config;
