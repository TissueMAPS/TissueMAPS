interface Serialized<T> {

}

interface Deserializer<T> {
    deserialize(obj: Serialized<T>): ng.IPromise<T>;
}

interface Serializable<T> {
    serialize(): ng.IPromise<Serialized<T>>;
}
