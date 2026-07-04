import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, Image, ActivityIndicator, FlatList } from "react-native";
import { useRoute, RouteProp } from "@react-navigation/native";
import { fetchCollection } from "../api";
import { imageUrl } from "../api";

type Params = { CollectionDetail: { slug: string } };

export default function CollectionDetailScreen() {
  const route = useRoute<RouteProp<Params, "CollectionDetail">>();
  const slug = route.params?.slug;
  const [collection, setCollection] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchCollection(slug);
        if (!cancelled) setCollection(data);
      } catch {
        if (!cancelled) setCollection(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) return <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />;
  if (!collection) return <Text style={styles.empty}>Collection not found</Text>;

  const cover = collection.cover_image_url || imageUrl(collection.cover_image);
  const looks = collection.looks || [];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {cover ? (
        <Image source={{ uri: cover }} style={styles.cover} />
      ) : (
        <View style={[styles.cover, styles.coverPlaceholder]}>
          <Text style={styles.coverLetter}>{collection.name?.charAt(0) || "C"}</Text>
        </View>
      )}
      <Text style={styles.title}>{collection.name}</Text>
      <Text style={styles.meta}>{collection.year}{collection.season ? ` · ${collection.season}` : ""}</Text>
      {collection.designer ? <Text style={styles.designer}>by {collection.designer}</Text> : null}
      {collection.description ? <Text style={styles.desc}>{collection.description}</Text> : null}
      {looks.length > 0 && (
        <>
          <Text style={styles.section}>Looks</Text>
          <FlatList
            data={looks}
            horizontal
            keyExtractor={(item) => String(item.id)}
            renderItem={({ item }) => {
              const img = item.image_url || imageUrl(item.image);
              return (
                <View style={styles.look}>
                  {img ? (
                    <Image source={{ uri: img }} style={styles.lookImage} />
                  ) : (
                    <View style={[styles.lookImage, styles.lookPlaceholder]}>
                      <Text style={styles.lookNum}>{item.look_number}</Text>
                    </View>
                  )}
                  {item.title ? <Text style={styles.lookTitle}>{item.title}</Text> : null}
                </View>
              );
            }}
            contentContainerStyle={styles.looksList}
            showsHorizontalScrollIndicator={false}
          />
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  content: { padding: 20, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: "center", backgroundColor: "#0E0E0F" },
  empty: { color: "#666", textAlign: "center", marginTop: 48 },
  cover: { width: "100%", height: 220, borderRadius: 12, backgroundColor: "#1a1a1c" },
  coverPlaceholder: { justifyContent: "center", alignItems: "center" },
  coverLetter: { color: "#D8B57A", fontSize: 64, fontWeight: "700" },
  title: { color: "#fff", fontSize: 24, fontWeight: "700", marginTop: 16 },
  meta: { color: "#888", fontSize: 14, marginTop: 4 },
  designer: { color: "#D8B57A", fontSize: 14, marginTop: 4 },
  desc: { color: "#ccc", fontSize: 15, marginTop: 12, lineHeight: 22 },
  section: { color: "#fff", fontSize: 18, fontWeight: "600", marginTop: 24, marginBottom: 12 },
  looksList: { paddingRight: 20 },
  look: { marginRight: 16, width: 140 },
  lookImage: { width: 140, height: 180, borderRadius: 8, backgroundColor: "#1a1a1c" },
  lookPlaceholder: { justifyContent: "center", alignItems: "center" },
  lookNum: { color: "#D8B57A", fontSize: 24, fontWeight: "700" },
  lookTitle: { color: "#ccc", fontSize: 12, marginTop: 6 },
});
