import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, FlatList, Image } from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { useAuth } from "../auth-context";
import { fetchMyDesigns } from "../api";
import { imageUrl } from "../api";

export default function AccountScreen() {
  const { user, logout, loading: authLoading } = useAuth();
  const [designs, setDesigns] = useState<any[]>([]);
  const [loadingDesigns, setLoadingDesigns] = useState(false);
  const nav = useNavigation<any>();

  const loadMyDesigns = async () => {
    if (!user) return;
    setLoadingDesigns(true);
    try {
      const data = await fetchMyDesigns();
      setDesigns(Array.isArray(data) ? data : []);
    } catch {
      setDesigns([]);
    } finally {
      setLoadingDesigns(false);
    }
  };

  useFocusEffect(
    React.useCallback(() => {
      if (user) loadMyDesigns();
    }, [user])
  );

  if (authLoading) {
    return <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />;
  }

  if (!user) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Account</Text>
        <Text style={styles.subtitle}>Sign in to access your profile and designs</Text>
        <TouchableOpacity style={styles.button} onPress={() => nav.navigate("Login")}>
          <Text style={styles.buttonText}>Sign in</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => nav.navigate("Signup")}>
          <Text style={styles.link}>Create an account</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;
  const pic = user.profile?.profile_image_url;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        {pic ? (
          <Image source={{ uri: pic }} style={styles.avatar} />
        ) : (
          <View style={[styles.avatar, styles.avatarPlaceholder]}>
            <Text style={styles.avatarText}>{(name || "?").charAt(0)}</Text>
          </View>
        )}
        <Text style={styles.name}>{name}</Text>
        <Text style={styles.email}>{user.email}</Text>
      </View>
      <Text style={styles.section}>My designs</Text>
      {loadingDesigns ? (
        <ActivityIndicator color="#D8B57A" style={styles.designsLoader} />
      ) : designs.length === 0 ? (
        <Text style={styles.empty}>No designs yet</Text>
      ) : (
        <FlatList
          data={designs}
          scrollEnabled={false}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <View style={styles.designRow}>
              {item.cover_image ? (
                <Image source={{ uri: imageUrl(item.cover_image) ?? undefined }} style={styles.designThumb} />
              ) : (
                <View style={[styles.designThumb, styles.thumbPlaceholder]}>
                  <Text style={styles.thumbText}>{item.title?.charAt(0) || "D"}</Text>
                </View>
              )}
              <Text style={styles.designTitle}>{item.title}</Text>
            </View>
          )}
        />
      )}
      <TouchableOpacity style={styles.logout} onPress={logout}>
        <Text style={styles.logoutText}>Sign out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  content: { padding: 24, paddingBottom: 48 },
  loader: { flex: 1, justifyContent: "center", backgroundColor: "#0E0E0F" },
  title: { fontSize: 24, fontWeight: "700", color: "#fff", marginBottom: 8 },
  subtitle: { fontSize: 15, color: "#888", marginBottom: 24 },
  button: { backgroundColor: "#D8B57A", padding: 16, borderRadius: 8, alignItems: "center", marginBottom: 12 },
  buttonText: { color: "#0E0E0F", fontWeight: "600", fontSize: 16 },
  link: { color: "#D8B57A", textAlign: "center", fontSize: 14 },
  header: { alignItems: "center", marginBottom: 24 },
  avatar: { width: 80, height: 80, borderRadius: 40 },
  avatarPlaceholder: { backgroundColor: "#2a2a2c", justifyContent: "center", alignItems: "center" },
  avatarText: { color: "#D8B57A", fontSize: 32, fontWeight: "700" },
  name: { color: "#fff", fontSize: 22, fontWeight: "700", marginTop: 12 },
  email: { color: "#888", fontSize: 14, marginTop: 4 },
  section: { color: "#fff", fontSize: 18, fontWeight: "600", marginBottom: 12 },
  designsLoader: { marginVertical: 16 },
  empty: { color: "#666", marginBottom: 16 },
  designRow: { flexDirection: "row", alignItems: "center", backgroundColor: "#1a1a1c", padding: 12, borderRadius: 8, marginBottom: 8 },
  designThumb: { width: 48, height: 48, borderRadius: 6 },
  thumbPlaceholder: { backgroundColor: "#2a2a2c", justifyContent: "center", alignItems: "center" },
  thumbText: { color: "#D8B57A", fontSize: 18, fontWeight: "600" },
  designTitle: { color: "#fff", marginLeft: 12, fontSize: 15 },
  logout: { marginTop: 32, padding: 16, alignItems: "center", borderWidth: 1, borderColor: "#444", borderRadius: 8 },
  logoutText: { color: "#cc6666", fontSize: 16 },
});
