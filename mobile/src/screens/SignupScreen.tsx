import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform, ScrollView } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../auth-context";

export default function SignupScreen() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const nav = useNavigation<any>();

  const handleSignup = async () => {
    if (!username.trim()) {
      Alert.alert("Error", "Enter a username");
      return;
    }
    if (!email.trim()) {
      Alert.alert("Error", "Enter your email");
      return;
    }
    if (!password || password.length < 8) {
      Alert.alert("Error", "Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await register(username.trim(), email.trim().toLowerCase(), password);
      nav.replace("MainTabs");
    } catch (e: any) {
      const msg = e?.data?.errors
        ? Object.entries(e.data.errors).map(([k, v]) => `${k}: ${(v as string[]).join(", ")}`).join("\n")
        : e?.data?.error || e?.message || "Registration failed";
      Alert.alert("Sign up failed", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Create account</Text>
        <TextInput
          style={styles.input}
          placeholder="Username"
          placeholderTextColor="#666"
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#666"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="Password (min 8 characters)"
          placeholderTextColor="#666"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
        <TouchableOpacity style={styles.button} onPress={handleSignup} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign up</Text>}
        </TouchableOpacity>
        <TouchableOpacity onPress={() => nav.goBack()}>
          <Text style={styles.link}>Already have an account? Sign in</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  scroll: { padding: 24, paddingTop: 48 },
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
