import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.chattingapp.app',
  appName: 'ChattingApp',
  webDir: 'dist',
  server: {
    androidScheme: 'https'
  }
};

export default config;
