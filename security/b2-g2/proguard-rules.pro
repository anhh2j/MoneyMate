# Only the target facade is a stable instrumentation entry point.
# Provider/JNI handling otherwise uses the standard optimize configuration.
-keep,allowoptimization class com.app.moneymate.b2g2.B2KdfProbe { public *; }

# P08: exact shared APIs referenced by the P07 minified runner DEX.
-keep class androidx.tracing.Trace {
    public static void beginSection(java.lang.String);
    public static void endSection();
    public static void forceEnableAppTracing();
}

# P11: exact runner initialization ABI; PO6361729695, bytecode evidence P10.
-keep class kotlin.jvm.internal.Lambda {
    public <init>(int);
    public int getArity();
}
-keep interface kotlin.jvm.internal.FunctionBase {
    public int getArity();
}
-keep interface kotlin.Function {
}
-keep interface kotlin.jvm.functions.Function0 {
    public java.lang.Object invoke();
}
-keep interface kotlin.Lazy {
    public java.lang.Object getValue();
}
-keep class kotlin.LazyKt {
}
-keep class kotlin.LazyKt__LazyKt {
}
-keep class kotlin.LazyKt__LazyJVMKt {
    public static kotlin.Lazy lazy(kotlin.jvm.functions.Function0);
}
-keep class kotlin.SynchronizedLazyImpl {
    public <init>(kotlin.jvm.functions.Function0,java.lang.Object);
    public <init>(kotlin.jvm.functions.Function0,java.lang.Object,int,kotlin.jvm.internal.DefaultConstructorMarker);
    public java.lang.Object getValue();
}
-keep class kotlin.UNINITIALIZED_VALUE {
    public static final kotlin.UNINITIALIZED_VALUE INSTANCE;
}
-keep class kotlin.jvm.internal.Intrinsics {
    public static void checkNotNullParameter(java.lang.Object,java.lang.String);
}
-keep class kotlin.jvm.internal.DefaultConstructorMarker {
}
