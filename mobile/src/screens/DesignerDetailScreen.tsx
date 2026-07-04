import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, Image, ActivityIndicator } from "react-native";
import { useRoute, RouteProp } from "@react-navigation/native";
import { fetchDesigner } from "../api";
import { imageUrl } from "../api";

type Params = { DesignerDetail: { user_id: number } };

export default function DesignerDetailScreen() {
  const route = useRoute<RouteProp<Params, "DesignerDetail">>();
  const user_id = route.params?.user_id;
  const [designer, setDesigner] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user_id == null) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchDesigner(user_id);
        if (!cancelled) setDesigner(data);
      } catch {
        if (!cancelled) setDesigner(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [user_id]);

  if (loading) return <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />;
  if (!designer) return <Text style={styles.empty}>Designer not found</Text>;

  const name = [designer.first_name, designer.last_name].filter(Boolean).join(" ") || designer.username;
  const pic = designer.profile_image_url || imageUrl(designer.profile_image);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {pic ? (
        <Image source={{ uri: pic }} style={styles.cover} />
      ) : (
        <View style={[styles.cover, styles.coverPlaceholder]}>
          <Text style={styles.coverLetter}>{(name || "?").charAt(0)}</Text>
        </View>
      )}
      <Text style={styles.name}>{name}</Text>
      {designer.specialization ? <Text style={styles.spec}>{designer.specialization}</Text> : null}
      {designer.bio ? <Text style={styles.bio}>{designer.bio}</Text> : null}
      {designer.location ? <Text style={styles.meta}>📍 {designer.location}</Text> : null}
      {designer.portfolio_website ? (
        <Text style={styles.link}>{designer.portfolio_website}</Text>
      ) : null}
      {designer.instagram_handle ? (
        <Text style={styles.meta}>Instagram: @{designer.instagram_handle}</Text>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  content: { padding: 20, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: "center", backgroundColor: "#0E0E0F" },
  empty: { color: "#666", textAlign: "center", marginTop: 48 },
  cover: { width: "100%", height: 200, borderRadius: 12, backgroundColor: "#1a1a1c" },
  coverPlaceholder: { justifyContent: "center", alignItems: "center" },
  coverLetter: { color: "#D8B57A", fontSize: 64, fontWeight: "700" },
  name: { color: "#fff", fontSize: 24, fontWeight: "700", marginTop: 16 },
  spec: { color: "#D8B57A", fontSize: 15, marginTop: 4 },
  bio: { color: "#ccc", fontSize: 15, marginTop: 12, lineHeight: 22 },
  meta: { color: "#888", fontSize: 14, marginTop: 8 },
  link: { color: "#D8B57A", fontSize: 14, marginTop: 8 },
});
