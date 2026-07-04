import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Modal,
  FlatList,
} from "react-native";
import { fetchNewOrderOptions, submitDressOrder, fetchDesigners } from "../api";

type Option = { value: string; label: string };

export default function NewOrdersScreen() {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [options, setOptions] = useState<{
    dress_types: Option[];
    fabric_types: Option[];
    wool_types: Option[];
    fabric_textures: Option[];
    formal_subcategories: Option[];
  } | null>(null);
  const [designers, setDesigners] = useState<any[]>([]);

  const [phone, setPhone] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [dressType, setDressType] = useState<Option | null>(null);
  const [formalSubcategory, setFormalSubcategory] = useState<Option | null>(null);
  const [shoulderWidth, setShoulderWidth] = useState("");
  const [chest, setChest] = useState("");
  const [sleeveShort, setSleeveShort] = useState("");
  const [sleeveWrist, setSleeveWrist] = useState("");
  const [fabricType, setFabricType] = useState<Option | null>(null);
  const [woolType, setWoolType] = useState<Option | null>(null);
  const [texture, setTexture] = useState<Option | null>(null);
  const [designer, setDesigner] = useState<any | null>(null);

  const [pickerModal, setPickerModal] = useState<{
    type: string;
    options: Option[] | any[];
    onSelect: (item: any) => void;
  } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [opts, dlist] = await Promise.all([
          fetchNewOrderOptions(),
          fetchDesigners(),
        ]);
        setOptions(opts);
        setDesigners(Array.isArray(dlist) ? dlist : []);
      } catch {
        setOptions(null);
        setDesigners([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const openPicker = (type: string, opts: Option[] | any[], onSelect: (item: any) => void) => {
    setPickerModal({ type, options: opts, onSelect });
  };

  const submit = async () => {
    const phoneDigits = (phone || "").replace(/\D/g, "");
    const emailValue = (customerEmail || "").trim();
    if (phoneDigits.length < 7) {
      Alert.alert("Phone required", "Enter a valid phone number (at least 7 digits)");
      return;
    }
    if (emailValue && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue)) {
      Alert.alert("Invalid email", "Enter a valid email address to receive order confirmation");
      return;
    }
    if (!designer?.user_id) {
      Alert.alert("Designer required", "Select a designer to send your order to");
      return;
    }
    setSubmitting(true);
    try {
      const res = await submitDressOrder({
        phone,
        customer_email: emailValue,
        designer_id: designer.user_id,
        dress_type: dressType?.value || "",
        dress_label: dressType?.label || "",
        formal_subcategory: formalSubcategory?.value || "",
        shoulder_width: shoulderWidth || undefined,
        chest: chest || undefined,
        sleeve_short: sleeveShort || undefined,
        sleeve_wrist: sleeveWrist || undefined,
        fabric_type: fabricType?.value || "",
        fabric_label: fabricType?.label || "",
        wool_type: woolType?.value || "",
        fabric_texture: texture?.value || "",
      });
      Alert.alert("Order sent", res.message);
      setCustomerEmail("");
      setDressType(null);
      setFormalSubcategory(null);
      setShoulderWidth("");
      setChest("");
      setSleeveShort("");
      setSleeveWrist("");
      setFabricType(null);
      setWoolType(null);
      setTexture(null);
      setDesigner(null);
    } catch (e: any) {
      Alert.alert("Error", e?.data?.error || e?.message || "Failed to submit order");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !options) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#D8B57A" />
        <Text style={styles.loadingText}>Loading…</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Orders — Dresses</Text>
      <Text style={styles.subtitle}>Select dress type, measurements, fabric, and designer. Add your email to receive order confirmation.</Text>

      {/* Phone */}
      <Text style={styles.label}>Phone number *</Text>
      <TextInput
        style={styles.input}
        placeholder="e.g. +1 555 123 4567"
        placeholderTextColor="#666"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
      />
      <Text style={styles.label}>Email for confirmation</Text>
      <TextInput
        style={styles.input}
        placeholder="you@example.com"
        placeholderTextColor="#666"
        value={customerEmail}
        onChangeText={setCustomerEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
      />

      {/* Dress type */}
      <Text style={styles.label}>Dress type</Text>
      <View style={styles.chipRow}>
        {options.dress_types.filter((o) => o.value).map((o) => (
          <TouchableOpacity
            key={o.value}
            style={[styles.chip, dressType?.value === o.value && styles.chipSelected]}
            onPress={() => {
              setDressType(o);
              if (o.value !== "formal") setFormalSubcategory(null);
            }}
          >
            <Text style={[styles.chipText, dressType?.value === o.value && styles.chipTextSelected]}>
              {o.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Formal subcategory */}
      {dressType?.value === "formal" && options.formal_subcategories.filter((o) => o.value).length > 0 && (
        <>
          <Text style={styles.label}>Formal sub-category</Text>
          <TouchableOpacity
            style={styles.selectBtn}
            onPress={() => openPicker("formal", options.formal_subcategories.filter((o) => o.value), setFormalSubcategory)}
          >
            <Text style={styles.selectBtnText}>{formalSubcategory?.label || "Select sub-category"}</Text>
          </TouchableOpacity>
        </>
      )}

      {/* Measurements */}
      <Text style={styles.label}>Measurements (cm)</Text>
      <View style={styles.row2}>
        <View style={styles.half}>
          <Text style={styles.smallLabel}>Shoulder width</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g. 42"
            placeholderTextColor="#666"
            value={shoulderWidth}
            onChangeText={setShoulderWidth}
            keyboardType="decimal-pad"
          />
        </View>
        <View style={styles.half}>
          <Text style={styles.smallLabel}>Chest</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g. 95"
            placeholderTextColor="#666"
            value={chest}
            onChangeText={setChest}
            keyboardType="decimal-pad"
          />
        </View>
      </View>
      <View style={styles.row2}>
        <View style={styles.half}>
          <Text style={styles.smallLabel}>Short sleeve</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g. 18"
            placeholderTextColor="#666"
            value={sleeveShort}
            onChangeText={setSleeveShort}
            keyboardType="decimal-pad"
          />
        </View>
        <View style={styles.half}>
          <Text style={styles.smallLabel}>Wrist length</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g. 58"
            placeholderTextColor="#666"
            value={sleeveWrist}
            onChangeText={setSleeveWrist}
            keyboardType="decimal-pad"
          />
        </View>
      </View>

      {/* Fabric type */}
      <Text style={styles.label}>Fabric type</Text>
      <View style={styles.chipRow}>
        {options.fabric_types.filter((o) => o.value).map((o) => (
          <TouchableOpacity
            key={o.value}
            style={[styles.chip, fabricType?.value === o.value && styles.chipSelected]}
            onPress={() => {
              setFabricType(o);
              if (o.value !== "wool") setWoolType(null);
            }}
          >
            <Text style={[styles.chipText, fabricType?.value === o.value && styles.chipTextSelected]}>
              {o.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Wool type */}
      {fabricType?.value === "wool" && options.wool_types.filter((o) => o.value).length > 0 && (
        <>
          <Text style={styles.label}>Wool type</Text>
          <TouchableOpacity
            style={styles.selectBtn}
            onPress={() => openPicker("wool", options.wool_types.filter((o) => o.value), setWoolType)}
          >
            <Text style={styles.selectBtnText}>{woolType?.label || "Select wool type"}</Text>
          </TouchableOpacity>
        </>
      )}

      {/* Texture */}
      <Text style={styles.label}>Texture</Text>
      <TouchableOpacity
        style={styles.selectBtn}
        onPress={() => openPicker("texture", options.fabric_textures, setTexture)}
      >
        <Text style={styles.selectBtnText}>{texture?.label || "Select texture"}</Text>
      </TouchableOpacity>

      {/* Designer */}
      <Text style={styles.label}>Designer *</Text>
      <TouchableOpacity
        style={styles.selectBtn}
        onPress={() =>
          openPicker(
            "designer",
            designers,
            (d: any) => setDesigner(d)
          )
        }
      >
        <Text style={styles.selectBtnText}>
          {designer
            ? [designer.first_name, designer.last_name].filter(Boolean).join(" ") || designer.username
            : "Select designer"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
        onPress={submit}
        disabled={submitting}
      >
        {submitting ? (
          <ActivityIndicator color="#fff" size="small" />
        ) : (
          <Text style={styles.submitBtnText}>Submit order</Text>
        )}
      </TouchableOpacity>

      {/* Picker modal */}
      <Modal
        visible={!!pickerModal}
        transparent
        animationType="slide"
        onRequestClose={() => setPickerModal(null)}
      >
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setPickerModal(null)}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {pickerModal?.type === "designer" ? "Select designer" : "Select option"}
            </Text>
            <FlatList
              data={pickerModal?.options || []}
              keyExtractor={(item, idx) =>
                pickerModal?.type === "designer" ? String(item.user_id) : (item as Option).value || String(idx)
              }
              renderItem={({ item }) => {
                const label =
                  pickerModal?.type === "designer"
                    ? [item.first_name, item.last_name].filter(Boolean).join(" ") || item.username
                    : (item as Option).label;
                return (
                  <TouchableOpacity
                    style={styles.modalItem}
                    onPress={() => {
                      pickerModal?.onSelect(item);
                      setPickerModal(null);
                    }}
                  >
                    <Text style={styles.modalItemText}>{label}</Text>
                  </TouchableOpacity>
                );
              }}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  content: { padding: 20, paddingBottom: 48 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0E0E0F" },
  loadingText: { color: "#888", marginTop: 12 },
  title: { fontSize: 24, fontWeight: "700", color: "#fff", marginBottom: 6 },
  subtitle: { fontSize: 14, color: "#888", marginBottom: 24 },
  label: { fontSize: 16, fontWeight: "600", color: "#D8B57A", marginTop: 16, marginBottom: 8 },
  smallLabel: { fontSize: 13, color: "#888", marginBottom: 4 },
  input: {
    backgroundColor: "#1a1a1c",
    borderWidth: 1,
    borderColor: "#2a2a2c",
    borderRadius: 8,
    padding: 12,
    color: "#fff",
    fontSize: 16,
  },
  row2: { flexDirection: "row", gap: 12 },
  half: { flex: 1 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    backgroundColor: "#1a1a1c",
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#2a2a2c",
  },
  chipSelected: { borderColor: "#D8B57A", backgroundColor: "rgba(216,181,122,0.15)" },
  chipText: { color: "#888", fontSize: 14 },
  chipTextSelected: { color: "#D8B57A", fontWeight: "600" },
  selectBtn: {
    backgroundColor: "#1a1a1c",
    borderWidth: 1,
    borderColor: "#2a2a2c",
    borderRadius: 8,
    padding: 14,
  },
  selectBtnText: { color: "#fff", fontSize: 16 },
  submitBtn: {
    backgroundColor: "#D8B57A",
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 28,
  },
  submitBtnDisabled: { opacity: 0.7 },
  submitBtnText: { color: "#0E0E0F", fontSize: 17, fontWeight: "600" },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: "#1a1a1c",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: "60%",
  },
  modalTitle: { color: "#fff", fontSize: 18, fontWeight: "600", padding: 16 },
  modalItem: { padding: 16, borderTopWidth: 1, borderTopColor: "#2a2a2c" },
  modalItemText: { color: "#fff", fontSize: 16 },
});
