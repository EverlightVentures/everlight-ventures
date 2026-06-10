module.exports = {
  presets: ['module:@react-native/babel-preset'],
  plugins: [
    [
      'module-resolver',
      {
        root: ['./src'],
        alias: {
          '@': './src',
          '@components': './src/components',
          '@screens': './src/screens',
          '@services': './src/services',
          '@store': './src/store',
          '@hooks': './src/hooks',
          '@utils': './src/utils',
          '@config': './src/config',
          '@types': './src/types',
          '@assets': './src/assets',
        },
      },
    ],
    // Reanimated plugin must be listed last
    'react-native-reanimated/plugin',
  ],
};
