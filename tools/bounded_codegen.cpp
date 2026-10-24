// Optional LLVM plugin for very large lifted functions. Keep scalar IR optimization, but bound the
// backend's expensive frequency/register-allocation work; smaller functions retain optimized allocation.
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Plugins/PassPlugin.h"
#include "llvm/IR/PassInstrumentation.h"
#include "llvm/IR/Module.h"
using namespace llvm;

struct BoundBackend : PassInfoMixin<BoundBackend> {
    PreservedAnalyses run(Module &M, ModuleAnalysisManager &) {
        for (auto &F : M) {
            if (F.isDeclaration() || (F.size() <= 128 && F.getInstructionCount() <= 5000)) continue;
            F.removeFnAttr(Attribute::AlwaysInline);
            F.addFnAttr(Attribute::NoInline);
            F.addFnAttr(Attribute::OptimizeNone);
        }
        return PreservedAnalyses::none();
    }
};

extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
    return {LLVM_PLUGIN_API_VERSION, "SavageWindBoundedBackend", "1", [](PassBuilder &PB) {
        if (auto *PIC = PB.getPassInstrumentationCallbacks())
            PIC->registerShouldRunOptionalPassCallback([](StringRef Name, Any) {
                return Name != "LICMPass" && !Name.contains("Loop");
            });
        PB.registerOptimizerLastEPCallback([](ModulePassManager &MPM, OptimizationLevel, ThinOrFullLTOPhase) {
            MPM.addPass(BoundBackend());
        });
    }};
}
