import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from '@components/atoms/Icon';
import { theme } from '@config/theme';

// Screens
import HomeScreen from '@screens/game/HomeScreen';
import GameScreen from '@screens/game/GameScreen';
import ResultsScreen from '@screens/game/ResultsScreen';
import RouletteScreen from '@screens/game/RouletteScreen';
import ChecklistScreen from '@screens/game/ChecklistScreen';
import StatsScreen from '@screens/profile/StatsScreen';
import AchievementsScreen from '@screens/profile/AchievementsScreen';

// Types
import type {
  RootStackParamList,
  MainTabParamList,
  HomeStackParamList,
  ProfileStackParamList,
} from './types';

const RootStack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();
const HomeStack = createNativeStackNavigator<HomeStackParamList>();
const ProfileStack = createNativeStackNavigator<ProfileStackParamList>();

// Temporary placeholder component for tabs
const PlaceholderScreen = ({ title }: { title: string }) => {
  const { View } = require('react-native');
  const { GradientBackground, Text } = require('@components/atoms');
  return (
    <GradientBackground>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <Text variant="h2">{title}</Text>
      </View>
    </GradientBackground>
  );
};

// Home Stack Navigator (includes game screens)
const HomeStackNavigator = () => {
  return (
    <HomeStack.Navigator
      screenOptions={{
        headerShown: false,
        animation: 'slide_from_right',
      }}
    >
      <HomeStack.Screen name="Home" component={HomeScreen} />
      <HomeStack.Screen name="Game" component={GameScreen} />
      <HomeStack.Screen name="Results" component={ResultsScreen} />
      <HomeStack.Screen name="Roulette" component={RouletteScreen} />
      <HomeStack.Screen name="Checklist" component={ChecklistScreen} />
    </HomeStack.Navigator>
  );
};

// Profile Stack Navigator (includes stats and achievements)
const ProfileStackNavigator = () => {
  const { View } = require('react-native');
  const { GradientBackground, Text, Button } = require('@components/atoms');

  const ProfileHomeScreen = ({ navigation }: any) => {
    return (
      <GradientBackground>
        <View style={{ flex: 1, padding: 24, justifyContent: 'center' }}>
          <Text variant="displayMedium" align="center" style={{ marginBottom: 32 }}>
            Profile
          </Text>
          <Button
            title="View Stats"
            variant="primary"
            size="large"
            fullWidth
            onPress={() => navigation.navigate('Stats')}
            style={{ marginBottom: 16 }}
          />
          <Button
            title="View Achievements"
            variant="secondary"
            size="large"
            fullWidth
            onPress={() => navigation.navigate('Achievements')}
          />
        </View>
      </GradientBackground>
    );
  };

  return (
    <ProfileStack.Navigator
      screenOptions={{
        headerShown: false,
        animation: 'slide_from_right',
      }}
    >
      <ProfileStack.Screen name="Profile" component={ProfileHomeScreen} />
      <ProfileStack.Screen name="Stats" component={StatsScreen} />
      <ProfileStack.Screen name="Achievements" component={AchievementsScreen} />
    </ProfileStack.Navigator>
  );
};

// Main Bottom Tabs
const MainTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: theme.colors.graphite,
          borderTopColor: theme.colors.mediumGray,
          borderTopWidth: 1,
          paddingBottom: 8,
          paddingTop: 8,
          height: 60,
        },
        tabBarActiveTintColor: theme.colors.champagneGold,
        tabBarInactiveTintColor: theme.colors.fogText,
        tabBarLabelStyle: {
          fontFamily: 'Inter-Medium',
          fontSize: 12,
        },
      }}
    >
      <Tab.Screen
        name="HomeTab"
        component={HomeStackNavigator}
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size }) => <Icon name="home" size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="DecksTab"
        children={() => <PlaceholderScreen title="Decks" />}
        options={{
          title: 'Decks',
          tabBarIcon: ({ color, size }) => <Icon name="layers" size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="ShopTab"
        children={() => <PlaceholderScreen title="Shop" />}
        options={{
          title: 'Shop',
          tabBarIcon: ({ color, size }) => (
            <Icon name="shopping-bag" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="ProfileTab"
        component={ProfileStackNavigator}
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => <Icon name="user" size={size} color={color} />,
        }}
      />
    </Tab.Navigator>
  );
};

export const AppNavigator = () => {
  return (
    <NavigationContainer>
      <RootStack.Navigator
        screenOptions={{
          headerShown: false,
          animation: 'fade',
        }}
      >
        <RootStack.Screen name="Main" component={MainTabs} />
      </RootStack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;
