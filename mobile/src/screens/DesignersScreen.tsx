import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Image, TextInput, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { fetchDesigners } from "../api";
import { imageUrl } from "../api";

export default function DesignersScreen() {
  const [list, setList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const nav = useNavigation<any>();

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchDesigners(search || undefined);
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
    const name = [item.first_name, item.last_name].filter(Boolean).join(" ") || item.username;
    const pic = item.profile_image_url || imageUrl(item.profile_image);
    return (
      <TouchableOpacity
        style={styles.row}
        onPress={() => nav.navigate("DesignerDetail", { user_id: item.user_id })}
      >
        {pic ? (
          <Image source={{ uri: pic }} style={styles.avatar} />
        ) : (
          <View style={[styles.avatar, styles.avatarPlaceholder]}>
            <Text style={styles.avatarText}>{(name || "?").charAt(0)}</Text>
          </View>
        )}
        <View style={styles.rowText}>
          <Text style={styles.name}>{name}</Text>
          {item.specialization ? <Text style={styles.meta}>{item.specialization}</Text> : null}
          {item.location ? <Text style={styles.meta}>{item.location}</Text> : null}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="Search designers..."
        placeholderTextColor="#666"
        value={search}
        onChangeText={setSearch}
      />
      {loading ? (
        <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />
      ) : (
        <FlatList
          data={list}
          keyExtractor={(item) => String(item.user_id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<Text style={styles.empty}>No designers found</Text>}
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
  loader: { flex: 1, justifyContent: "center" },
  empty: { color: "#666", textAlign: "center", marginTop: 24 },
  row: {
    flexDirection: "row",
    backgroundColor: "#1a1a1c",
    padding: 14,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#2a2a2c",
  },
  avatar: { width: 56, height: 56, borderRadius: 28 },
  avatarPlaceholder: { backgroundColor: "#2a2a2c", justifyContent: "center", alignItems: "center" },
  avatarText: { color: "#D8B57A", fontSize: 22, fontWeight: "600" },
  rowText: { marginLeft: 14, flex: 1, justifyContent: "center" },
  name: { color: "#fff", fontSize: 17, fontWeight: "600" },
  meta: { color: "#888", fontSize: 13, marginTop: 2 },
});
