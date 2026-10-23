# Only the target facade is a stable instrumentation entry point.
# Provider/JNI handling otherwise uses the standard optimize configuration.
-keep,allowoptimization class com.app.moneymate.b2g2.B2KdfProbe { public *; }

# P08: exact shared APIs referenced by the P07 minified runner DEX.
-keep class androidx.tracing.Trace {
    public static void beginSection(java.lang.String);
    public static void endSection();
    public static void forceEnableAppTracing();
}
