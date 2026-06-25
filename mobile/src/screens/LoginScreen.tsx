import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../auth-context";

export default function LoginScreen() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const nav = useNavigation<any>();

  const handleLogin = async () => {
    if (!username.trim() || !password) {
      Alert.alert("Error", "Enter username and password");
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password);
      nav.replace("MainTabs");
    } catch (e: any) {
      Alert.alert("Login failed", e?.data?.error || e?.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.container}>
      <Text style={styles.title}>Sign in</Text>
      <TextInput
        style={styles.input}
        placeholder="Username"
        placeholderTextColor="#666"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
        autoCorrect={false}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#666"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign in</Text>}
      </TouchableOpacity>
      <TouchableOpacity onPress={() => nav.navigate("Signup")}>
        <Text style={styles.link}>Create an account</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F", padding: 24, justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "700", color: "#fff", marginBottom: 24 },
  input: {
    backgroundColor: "#1a1a1c",
    borderWidth: 1,
    borderColor: "#2a2a2c",
    borderRadius: 8,
    padding: 14,
    color: "#fff",
    marginBottom: 12,
    fontSize: 16,
  },
  button: {
    backgroundColor: "#D8B57A",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
    marginBottom: 16,
  },
  buttonText: { color: "#0E0E0F", fontWeight: "600", fontSize: 16 },
  link: { color: "#D8B57A", textAlign: "center", fontSize: 14 },
});
