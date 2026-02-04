import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Image, TextInput, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { fetchCollections } from "../api";
import { imageUrl } from "../api";

export default function CollectionsScreen() {
  const [list, setList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const nav = useNavigation<any>();

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchCollections(search || undefined);
      setList(Array.isArray(data) ? data : []);
    } catch {
      setList([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [search]);

  const renderItem = ({ item }: { item: any }) => {
    const pic = item.cover_image_url || imageUrl(item.cover_image);
    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => nav.navigate("CollectionDetail", { slug: item.slug })}
      >
        {pic ? (
          <Image source={{ uri: pic }} style={styles.image} />
        ) : (
          <View style={[styles.image, styles.imagePlaceholder]}>
            <Text style={styles.imageText}>{item.name?.charAt(0) || "C"}</Text>
          </View>
        )}
        <View style={styles.cardBody}>
          <Text style={styles.title}>{item.name}</Text>
          <Text style={styles.meta}>{item.year}{item.season ? ` · ${item.season}` : ""}</Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="Search collections..."
        placeholderTextColor="#666"
        value={search}
        onChangeText={setSearch}
      />
      {loading ? (
        <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />
      ) : (
        <FlatList
          data={list}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          numColumns={2}
          columnWrapperStyle={styles.row}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<Text style={styles.empty}>No collections found</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  search: {
    backgroundColor: "#1a1a1c",
    borderWidth: 1,
    borderColor: "#2a2a2c",
    borderRadius: 8,
    padding: 12,
    margin: 16,
    color: "#fff",
    fontSize: 16,
  },
  list: { padding: 16, paddingTop: 0 },
  row: { justifyContent: "space-between", marginBottom: 12 },
  loader: { flex: 1, justifyContent: "center" },
  empty: { color: "#666", textAlign: "center", marginTop: 24 },
  card: { width: "48%", backgroundColor: "#1a1a1c", borderRadius: 12, overflow: "hidden", borderWidth: 1, borderColor: "#2a2a2c" },
  image: { width: "100%", aspectRatio: 1 },
  imagePlaceholder: { backgroundColor: "#2a2a2c", justifyContent: "center", alignItems: "center" },
  imageText: { color: "#D8B57A", fontSize: 32, fontWeight: "700" },
  cardBody: { padding: 10 },
  title: { color: "#fff", fontSize: 14, fontWeight: "600" },
  meta: { color: "#888", fontSize: 12, marginTop: 2 },
});
