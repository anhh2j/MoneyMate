# Only the target facade is a stable instrumentation entry point.
# Provider/JNI handling otherwise uses the standard optimize configuration.
-keep,allowoptimization class com.app.moneymate.b2g2.B2KdfProbe { public *; }
