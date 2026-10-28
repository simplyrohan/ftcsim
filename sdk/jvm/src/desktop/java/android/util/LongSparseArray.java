package android.util;
import java.util.*;
/** JVM implementation for SDK thread bookkeeping; avoids Android VMRuntime allocation. */
public class LongSparseArray<E> implements Cloneable {
    private final NavigableMap<Long,E> values = new TreeMap<>();
    public LongSparseArray() { }
    public LongSparseArray(int capacity) { }
    public E get(long key) { return get(key, null); }
    public E get(long key, E fallback) { return values.getOrDefault(key, fallback); }
    public void put(long key, E value) { values.put(key, value); }
    public void append(long key, E value) { put(key, value); }
    public void delete(long key) { values.remove(key); }
    public void remove(long key) { values.remove(key); }
    public void removeAt(int index) { values.remove(keyAt(index)); }
    public void clear() { values.clear(); }
    public int size() { return values.size(); }
    public long keyAt(int index) { return new ArrayList<>(values.keySet()).get(index); }
    public E valueAt(int index) { return values.get(keyAt(index)); }
    public void setValueAt(int index, E value) { values.put(keyAt(index), value); }
    public int indexOfKey(long key) { return Collections.binarySearch(new ArrayList<>(values.keySet()), key); }
    public int indexOfValue(E value) { int i=0; for(E current:values.values()) { if(current==value)return i; i++; } return -1; }
    @Override public LongSparseArray<E> clone() { LongSparseArray<E> copy=new LongSparseArray<>(); copy.values.putAll(values); return copy; }
}
