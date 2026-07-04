import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "expo-status-bar";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { AuthProvider, useAuth } from "./src/auth-context";

import HomeScreen from "./src/screens/HomeScreen";
import DesignersScreen from "./src/screens/DesignersScreen";
import DesignerDetailScreen from "./src/screens/DesignerDetailScreen";
import CollectionsScreen from "./src/screens/CollectionsScreen";
import CollectionDetailScreen from "./src/screens/CollectionDetailScreen";
import EventsScreen from "./src/screens/EventsScreen";
import EventDetailScreen from "./src/screens/EventDetailScreen";
import AccountScreen from "./src/screens/AccountScreen";
import LoginScreen from "./src/screens/LoginScreen";
import SignupScreen from "./src/screens/SignupScreen";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#0E0E0F" },
        headerTintColor: "#fff",
        tabBarStyle: { backgroundColor: "#0E0E0F", borderTopColor: "#2a2a2c" },
        tabBarActiveTintColor: "#D8B57A",
        tabBarInactiveTintColor: "#666",
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: "Global Designer Hub" }} />
      <Tab.Screen name="Designers" component={DesignersScreen} />
      <Tab.Screen name="Collections" component={CollectionsScreen} />
      <Tab.Screen name="Events" component={EventsScreen} />
      <Tab.Screen name="Account" component={AccountScreen} options={{ title: "Account" }} />
    </Tab.Navigator>
  );
}

function AppNavigator() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color="#D8B57A" />
        <Text style={styles.loadingText}>Loading…</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={token ? "MainTabs" : "Login"}
        screenOptions={{
          headerStyle: { backgroundColor: "#0E0E0F" },
          headerTintColor: "#fff",
          contentStyle: { backgroundColor: "#0E0E0F" },
        }}
      >
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Signup" component={SignupScreen} options={{ title: "Create account" }} />
        <Stack.Screen name="MainTabs" component={MainTabs} options={{ headerShown: false }} />
        <Stack.Screen name="DesignerDetail" component={DesignerDetailScreen} options={{ title: "Designer" }} />
        <Stack.Screen name="CollectionDetail" component={CollectionDetailScreen} options={{ title: "Collection" }} />
        <Stack.Screen name="EventDetail" component={EventDetailScreen} options={{ title: "Event" }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <AppNavigator />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0E0E0F" },
  loadingText: { color: "#888", marginTop: 12 },
});
